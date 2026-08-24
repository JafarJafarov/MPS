from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_CEILING

from django.db import transaction
from django.utils import timezone

from planning.models import (
    ITKRequest,
    SAPOperation,
)
from planning.calendar_service import WorkCalendarService
from planning.azerbaijan_calendar import AzerbaijanCalendar2026

from .models import (
    ScheduledOperation,
    SchedulingRun,
    ScheduleSegment,
)

from .services import EligibilityEngine
from .priority import PriorityEngine
from .capacity_engine import CapacityEngine


class WeeklySchedulingEngine:
    """
    MPS-in əsas həftəlik Scheduling Engine-i.

    Axın:
    1. İTK sifarişlərini götürür.
    2. SAP operation-larını tapır.
    3. Eligibility yoxlayır.
    4. Priority / Due Date hesablayır.
    5. Capacity yoxlayır.
    6. Operation-u real gün və saatlara yerləşdirir.
    7. Nəticəni ScheduledOperation-a yazır.
    8. Gantt üçün ScheduleSegment yaradır.
    """

    WORK_START = time(8, 0)
    LUNCH_START = time(12, 0)
    LUNCH_END = time(13, 0)
    WORK_END = time(17, 0)

    SLOT_MINUTES = 15

    def __init__(self, weekly_plan):

        self.weekly_plan = weekly_plan

        self.eligibility_engine = EligibilityEngine()
        self.priority_engine = PriorityEngine()
        self.capacity_engine = CapacityEngine(
            weekly_plan
        )

        # (work_center_id, tarix, dəqiqə) -> istifadə olunan adam
        self.people_usage = {}

    # =====================================================
    # ƏSAS RUN
    # =====================================================

    @transaction.atomic
    def run(self):

        scheduling_run = SchedulingRun.objects.create(
            weekly_plan=self.weekly_plan,
            status="RUNNING",
        )

        try:

            # =================================================
            # WORK CALENDAR AUTO GENERATION
            # =================================================
            # Həftəlik proqram başlamazdan əvvəl həmin tarix
            # aralığının iş təqvimi avtomatik yaradılır.
            # Manual override edilmiş günlər qorunur.

            WorkCalendarService.generate_range(
                self.weekly_plan.start_date,
                self.weekly_plan.end_date,
            )

            # 2026 Azərbaycan rəsmi istehsalat təqvimini tətbiq et.
            if self.weekly_plan.year == 2026:
                AzerbaijanCalendar2026.apply()

            # Manual lock olmayan köhnə nəticələri sil.
            # Segmentlər CASCADE ilə avtomatik silinəcək.
            ScheduledOperation.objects.filter(
                weekly_plan=self.weekly_plan,
                is_locked=False,
            ).delete()

            # Manual kilidlənmiş işlərin resurslarını
            # əvvəlcədən rezerv edirik.
            self._load_locked_operations()

            operations = self._get_itk_operations()

            scheduling_run.total_operations = len(
                operations
            )

            eligible_items = []

            # =================================================
            # 1. ELIGIBILITY
            # =================================================

            for operation in operations:

                eligibility = (
                    self.eligibility_engine.check(
                        operation
                    )
                )

                if not eligibility.eligible:

                    self._save_not_scheduled(
                        operation=operation,
                        reason=eligibility.reason,
                    )

                    continue

                # =============================================
                # 2. PRIORITY / DUE DATE
                # =============================================

                priority_result = (
                    self.priority_engine.calculate(
                        operation=operation,
                        reference_date=(
                            self.weekly_plan.start_date
                        ),
                    )
                )

                if priority_result.due_date is None:

                    self._save_review(
                        operation=operation,
                        reason=priority_result.reason,
                        priority=priority_result.priority,
                    )

                    continue

                eligible_items.append(
                    {
                        "operation": operation,
                        "priority": priority_result,
                    }
                )

            # =================================================
            # 3. PRIORITY SORT
            # =================================================

            eligible_items.sort(
                key=self._priority_sort_key
            )

            # =================================================
            # 4. SCHEDULING
            # =================================================

            sequence = 1

            for item in eligible_items:

                operation = item["operation"]
                priority_result = item["priority"]

                result = self._schedule_operation(
                    operation
                )

                if result["success"]:

                    scheduled_operation = (
                        ScheduledOperation.objects.create(
                            weekly_plan=self.weekly_plan,

                            sap_operation=operation,

                            work_center=(
                                operation.work_center
                            ),

                            decision="SCHEDULED",

                            decision_reason=(
                                result["reason"]
                            ),

                            priority=(
                                priority_result.priority
                            ),

                            due_date=(
                                priority_result.due_date
                            ),

                            is_overdue=(
                                priority_result.is_overdue
                            ),

                            scheduled_date=(
                                result["start_date"]
                            ),

                            scheduled_start=(
                                result["start_time"]
                            ),

                            scheduled_end=(
                                result["end_time"]
                            ),

                            required_people=(
                                operation.required_people
                            ),

                            planned_mh=(
                                operation.planned_work_mh
                            ),

                            planned_duration_hours=(
                                operation
                                .calculated_duration_hours
                            ),

                            sequence=sequence,

                            scheduler_score=(
                                priority_result.score
                            ),
                        )
                    )

                    # Gantt segmentlərini yarat
                    self._create_segments(
                        scheduled_operation=(
                            scheduled_operation
                        ),
                        slots=result["slots"],
                        required_people=(
                            operation.required_people
                        ),
                    )

                    sequence += 1

                else:

                    self._save_not_scheduled(
                        operation=operation,
                        reason=result["reason"],
                        priority_result=priority_result,
                    )

            # =================================================
            # 5. RUN STATISTICS
            # =================================================

            results = (
                ScheduledOperation.objects.filter(
                    weekly_plan=self.weekly_plan
                )
            )

            scheduling_run.scheduled_operations = (
                results.filter(
                    decision="SCHEDULED"
                ).count()
            )

            scheduling_run.not_scheduled_operations = (
                results.filter(
                    decision="NOT_SCHEDULED"
                ).count()
            )

            scheduling_run.review_operations = (
                results.filter(
                    decision="REVIEW"
                ).count()
            )

            total_mh = Decimal("0")

            for result_item in results.filter(
                decision="SCHEDULED"
            ):

                if result_item.planned_mh:

                    total_mh += (
                        result_item.planned_mh
                    )

            scheduling_run.total_planned_mh = (
                total_mh
            )

            scheduling_run.status = "COMPLETED"

            scheduling_run.completed_at = (
                timezone.now()
            )

            scheduling_run.save()

            return scheduling_run

        except Exception as error:

            scheduling_run.status = "FAILED"

            scheduling_run.error_message = str(
                error
            )

            scheduling_run.completed_at = (
                timezone.now()
            )

            scheduling_run.save()

            raise

    # =====================================================
    # İTK → SAP OPERATION
    # =====================================================

    def _get_itk_operations(self):

        itk_order_numbers = list(
            ITKRequest.objects
            .filter(
                weekly_plan=self.weekly_plan
            )
            .values_list(
                "order_number",
                flat=True
            )
        )

        if not itk_order_numbers:
            return []

        return list(
            SAPOperation.objects
            .filter(
                order__order_number__in=(
                    itk_order_numbers
                )
            )
            .select_related(
                "order",
                "work_center",
            )
        )

    # =====================================================
    # PRIORITY SORT
    # =====================================================

    def _priority_sort_key(
        self,
        item
    ):

        operation = item["operation"]
        result = item["priority"]

        return (
            0 if result.is_overdue else 1,

            result.due_date
            or date.max,

            result.priority
            if result.priority
            else 999,

            result.creation_date
            or date.max,

            operation.order.order_number,

            operation.operation_number,
        )

    # =====================================================
    # OPERATION SCHEDULING
    # =====================================================

    def _schedule_operation(
        self,
        operation
    ):

        work_center = operation.work_center

        required_people = Decimal(
            str(operation.required_people)
        )

        planned_mh = Decimal(
            str(operation.planned_work_mh)
        )

        # =================================================
        # WEEKLY CAPACITY CHECK
        # =================================================

        capacity_ok, capacity_reason = (
            self.capacity_engine.can_allocate(
                work_center=work_center,
                required_people=required_people,
                planned_mh=planned_mh,
            )
        )

        if not capacity_ok:

            return {
                "success": False,
                "reason": capacity_reason,
            }

        # =================================================
        # DURATION
        # =================================================

        duration_hours = (
            planned_mh / required_people
        )

        required_minutes = int(
            (
                duration_hours
                * Decimal("60")
            ).to_integral_value(
                rounding=ROUND_CEILING
            )
        )

        required_slots = int(
            (
                Decimal(required_minutes)
                / Decimal(self.SLOT_MINUTES)
            ).to_integral_value(
                rounding=ROUND_CEILING
            )
        )

        # =================================================
        # HƏFTƏ DAXİLİ SLOT AXTARIŞI
        # =================================================

        slots = self._get_week_slots()

        if not slots:

            return {
                "success": False,
                "reason": (
                    "Həftə daxilində planlama "
                    "slotu yoxdur."
                ),
            }

        candidate_slots = []

        for slot in slots:

            if self._slot_has_people(
                work_center=work_center,
                work_date=slot["date"],
                minute=slot["minute"],
                required_people=required_people,
            ):

                candidate_slots.append(
                    slot
                )

                if (
                    len(candidate_slots)
                    >= required_slots
                ):

                    selected_slots = (
                        candidate_slots[
                            -required_slots:
                        ]
                    )

                    if self._slots_are_continuous(
                        selected_slots
                    ):

                        return (
                            self._commit_operation(
                                operation=operation,
                                slots=selected_slots,
                                required_people=(
                                    required_people
                                ),
                                planned_mh=(
                                    planned_mh
                                ),
                            )
                        )

            else:

                candidate_slots = []

        return {
            "success": False,

            "reason": (
                f"{work_center.code} üçün həftə "
                "daxilində tələb olunan "
                f"{required_people} nəfərlik "
                "uyğun vaxt intervalı tapılmadı."
            ),
        }

    # =====================================================
    # SLOT GENERATION
    # =====================================================

    def _get_week_slots(self):

        slots = []

        current_date = (
            self.weekly_plan.start_date
        )

        while (
            current_date
            <= self.weekly_plan.end_date
        ):

            # İş təqviminə əsasən yalnız
            # real iş günlərinə slot yaradırıq.
            if WorkCalendarService.is_working_day(
                current_date
            ):

                working_hours = (
                    WorkCalendarService
                    .get_working_hours(
                        current_date
                    )
                )

                if working_hours > 0:

                    # 08:00 → 12:00
                    slots.extend(
                        self._generate_slots(
                            current_date,
                            self.WORK_START,
                            self.LUNCH_START,
                        )
                    )

                    # 13:00 → 17:00
                    slots.extend(
                        self._generate_slots(
                            current_date,
                            self.LUNCH_END,
                            self.WORK_END,
                        )
                    )

            current_date += timedelta(
                days=1
            )

        return slots

    def _generate_slots(
        self,
        work_date,
        start_time,
        end_time,
    ):

        result = []

        current = datetime.combine(
            work_date,
            start_time
        )

        end = datetime.combine(
            work_date,
            end_time
        )

        while current < end:

            result.append(
                {
                    "date": work_date,

                    "minute": (
                        current.hour * 60
                        + current.minute
                    ),

                    "time": current.time(),
                }
            )

            current += timedelta(
                minutes=self.SLOT_MINUTES
            )

        return result

    # =====================================================
    # SLOT CONTINUITY
    # =====================================================

    def _slots_are_continuous(
        self,
        slots
    ):

        if not slots:
            return False

        for index in range(
            1,
            len(slots)
        ):

            previous = slots[
                index - 1
            ]

            current = slots[index]

            previous_dt = datetime.combine(
                previous["date"],
                previous["time"]
            )

            current_dt = datetime.combine(
                current["date"],
                current["time"]
            )

            expected = (
                previous_dt
                + timedelta(
                    minutes=self.SLOT_MINUTES
                )
            )

            # ---------------------------------------------
            # NAHAR KEÇİDİ
            # 11:45 slotu 12:00-da bitir.
            # Növbəti slot 13:00 ola bilər.
            # ---------------------------------------------

            if (
                previous["time"] == time(11, 45)
                and current["time"] == time(13, 0)
                and previous["date"] == current["date"]
            ):
                continue

            # ---------------------------------------------
            # NÖVBƏTİ İŞ GÜNÜNƏ KEÇİD
            # ---------------------------------------------

            if (
                current["date"] > previous["date"]
                and current["time"] == self.WORK_START
            ):
                continue

            if current_dt != expected:
                return False

        return True

    # =====================================================
    # HEADCOUNT SLOT CONTROL
    # =====================================================

    def _slot_has_people(
        self,
        work_center,
        work_date,
        minute,
        required_people,
    ):

        available_people = Decimal(
            str(
                self.capacity_engine
                .get_headcount(
                    work_center
                )
            )
        )

        key = (
            work_center.id,
            work_date,
            minute,
        )

        used_people = Decimal(
            str(
                self.people_usage.get(
                    key,
                    0
                )
            )
        )

        return (
            used_people
            + required_people
            <= available_people
        )

    # =====================================================
    # COMMIT OPERATION
    # =====================================================

    def _commit_operation(
        self,
        operation,
        slots,
        required_people,
        planned_mh,
    ):

        work_center = (
            operation.work_center
        )

        # ---------------------------------------------
        # Slotlarda headcount rezerv edilir
        # ---------------------------------------------

        for slot in slots:

            key = (
                work_center.id,
                slot["date"],
                slot["minute"],
            )

            current = Decimal(
                str(
                    self.people_usage.get(
                        key,
                        0
                    )
                )
            )

            self.people_usage[key] = (
                current
                + required_people
            )

        # ---------------------------------------------
        # Həftəlik MH rezerv edilir
        # ---------------------------------------------

        allocated = (
            self.capacity_engine.allocate(
                work_center,
                planned_mh
            )
        )

        if not allocated:

            # Slot rezervlərini geri qaytar
            for slot in slots:

                key = (
                    work_center.id,
                    slot["date"],
                    slot["minute"],
                )

                self.people_usage[
                    key
                ] -= required_people

            return {
                "success": False,

                "reason": (
                    "Capacity rezervasiyası "
                    "uğursuz oldu."
                ),
            }

        first_slot = slots[0]
        last_slot = slots[-1]

        end_datetime = (
            datetime.combine(
                last_slot["date"],
                last_slot["time"]
            )
            + timedelta(
                minutes=self.SLOT_MINUTES
            )
        )

        return {
            "success": True,

            "start_date": (
                first_slot["date"]
            ),

            "start_time": (
                first_slot["time"]
            ),

            "end_date": (
                end_datetime.date()
            ),

            "end_time": (
                end_datetime.time()
            ),

            # 8.6 üçün vacibdir.
            "slots": slots,

            "reason": (
                f"{work_center.code} üzrə "
                f"{required_people} nəfər və "
                f"{planned_mh} MH rezerv edildi."
            ),
        }

    # =====================================================
    # GANTT SEGMENTLƏRİNİN YARADILMASI
    # =====================================================

    def _create_segments(
        self,
        scheduled_operation,
        slots,
        required_people,
    ):
        """
        15 dəqiqəlik slotları Gantt üçün
        ayrı-ayrı iş segmentlərinə çevirir.

        Nahar və gün dəyişəndə yeni segment yaranır.
        """

        if not slots:
            return

        required_people = Decimal(
            str(required_people)
        )

        groups = []

        current_group = [
            slots[0]
        ]

        for slot in slots[1:]:

            previous = (
                current_group[-1]
            )

            previous_dt = datetime.combine(
                previous["date"],
                previous["time"]
            )

            current_dt = datetime.combine(
                slot["date"],
                slot["time"]
            )

            expected = (
                previous_dt
                + timedelta(
                    minutes=self.SLOT_MINUTES
                )
            )

            # Yalnız həqiqətən ardıcıl slotdursa
            # eyni Gantt segmentində saxla.
            if current_dt == expected:

                current_group.append(
                    slot
                )

            else:

                groups.append(
                    current_group
                )

                current_group = [
                    slot
                ]

        groups.append(
            current_group
        )

        segment_sequence = 1

        for group in groups:

            first_slot = group[0]
            last_slot = group[-1]

            start_time = (
                first_slot["time"]
            )

            end_datetime = (
                datetime.combine(
                    last_slot["date"],
                    last_slot["time"]
                )
                + timedelta(
                    minutes=self.SLOT_MINUTES
                )
            )

            duration_minutes = (
                len(group)
                * self.SLOT_MINUTES
            )

            duration_hours = (
                Decimal(duration_minutes)
                / Decimal("60")
            )

            segment_mh = (
                duration_hours
                * required_people
            )

            ScheduleSegment.objects.create(
                scheduled_operation=(
                    scheduled_operation
                ),

                work_date=(
                    first_slot["date"]
                ),

                start_time=(
                    start_time
                ),

                end_time=(
                    end_datetime.time()
                ),

                required_people=(
                    required_people
                ),

                segment_mh=(
                    segment_mh
                ),

                sequence=(
                    segment_sequence
                ),
            )

            segment_sequence += 1

    # =====================================================
    # LOCKED OPERATIONS
    # =====================================================

    def _load_locked_operations(self):

        locked = (
            ScheduledOperation.objects
            .filter(
                weekly_plan=self.weekly_plan,
                decision="SCHEDULED",
                is_locked=True,
            )
            .select_related(
                "work_center"
            )
            .prefetch_related(
                "segments"
            )
        )

        for item in locked:

            if (
                item.work_center is None
                or item.required_people is None
            ):
                continue

            # ---------------------------------------------
            # Əgər segmentlər varsa onları istifadə et
            # ---------------------------------------------

            segments = list(
                item.segments.all()
            )

            if segments:

                for segment in segments:

                    current = datetime.combine(
                        segment.work_date,
                        segment.start_time
                    )

                    end = datetime.combine(
                        segment.work_date,
                        segment.end_time
                    )

                    while current < end:

                        key = (
                            item.work_center.id,
                            current.date(),
                            (
                                current.hour * 60
                                + current.minute
                            ),
                        )

                        existing = Decimal(
                            str(
                                self.people_usage.get(
                                    key,
                                    0
                                )
                            )
                        )

                        self.people_usage[
                            key
                        ] = (
                            existing
                            + item.required_people
                        )

                        current += timedelta(
                            minutes=self.SLOT_MINUTES
                        )

            # ---------------------------------------------
            # Köhnə locked nəticədə segment yoxdursa
            # start/end istifadə et
            # ---------------------------------------------

            elif (
                item.scheduled_date is not None
                and item.scheduled_start is not None
                and item.scheduled_end is not None
            ):

                current = datetime.combine(
                    item.scheduled_date,
                    item.scheduled_start
                )

                end = datetime.combine(
                    item.scheduled_date,
                    item.scheduled_end
                )

                while current < end:

                    if not (
                        self.LUNCH_START
                        <= current.time()
                        < self.LUNCH_END
                    ):

                        key = (
                            item.work_center.id,
                            current.date(),
                            (
                                current.hour * 60
                                + current.minute
                            ),
                        )

                        existing = Decimal(
                            str(
                                self.people_usage.get(
                                    key,
                                    0
                                )
                            )
                        )

                        self.people_usage[
                            key
                        ] = (
                            existing
                            + item.required_people
                        )

                    current += timedelta(
                        minutes=self.SLOT_MINUTES
                    )

            # Həftəlik MH-ni də rezerv et.
            if item.planned_mh:

                self.capacity_engine.allocate(
                    item.work_center,
                    item.planned_mh
                )

    # =====================================================
    # SAVE — NOT SCHEDULED
    # =====================================================

    def _save_not_scheduled(
        self,
        operation,
        reason,
        priority_result=None,
    ):

        ScheduledOperation.objects.update_or_create(
            weekly_plan=self.weekly_plan,
            sap_operation=operation,

            defaults={
                "work_center": (
                    operation.work_center
                ),

                "decision": (
                    "NOT_SCHEDULED"
                ),

                "decision_reason": (
                    reason
                ),

                "priority": (
                    priority_result.priority
                    if priority_result
                    else operation.order.priority
                ),

                "due_date": (
                    priority_result.due_date
                    if priority_result
                    else None
                ),

                "is_overdue": (
                    priority_result.is_overdue
                    if priority_result
                    else False
                ),

                "scheduled_date": None,
                "scheduled_start": None,
                "scheduled_end": None,

                "required_people": (
                    operation.required_people
                ),

                "planned_mh": (
                    operation.planned_work_mh
                ),

                "planned_duration_hours": (
                    operation
                    .calculated_duration_hours
                ),

                "sequence": None,
            }
        )

    # =====================================================
    # SAVE — REVIEW
    # =====================================================

    def _save_review(
        self,
        operation,
        reason,
        priority=None,
    ):

        ScheduledOperation.objects.update_or_create(
            weekly_plan=self.weekly_plan,
            sap_operation=operation,

            defaults={
                "work_center": (
                    operation.work_center
                ),

                "decision": (
                    "REVIEW"
                ),

                "decision_reason": (
                    reason
                ),

                "priority": (
                    priority
                ),

                "due_date": None,
                "is_overdue": False,

                "scheduled_date": None,
                "scheduled_start": None,
                "scheduled_end": None,

                "required_people": (
                    operation.required_people
                ),

                "planned_mh": (
                    operation.planned_work_mh
                ),

                "planned_duration_hours": (
                    operation
                    .calculated_duration_hours
                ),

                "sequence": None,
            }
        )