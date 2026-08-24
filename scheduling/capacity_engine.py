from dataclasses import dataclass
from decimal import Decimal

from capacity.models import WeeklyCapacity


@dataclass
class CapacityResult:
    """
    Konkret WorkCenter üçün həftəlik
    capacity vəziyyətini saxlayır.
    """

    work_center_id: int
    work_center_code: str

    headcount: int

    productive_hours_per_day: Decimal
    working_days: int

    daily_capacity_mh: Decimal
    weekly_capacity_mh: Decimal

    allocated_mh: Decimal
    remaining_mh: Decimal

    utilization_percent: Decimal


class CapacityEngine:
    """
    WeeklyCapacity məlumatları əsasında
    scheduling üçün resurs idarəetməsi.
    """

    def __init__(self, weekly_plan):

        self.weekly_plan = weekly_plan

        self.capacities = {}

        self._load_capacities()

    def _load_capacities(self):
        """
        Seçilmiş həftənin bütün WorkCenter
        capacity məlumatlarını yaddaşa yükləyir.
        """

        weekly_capacities = (
            WeeklyCapacity.objects
            .filter(
                weekly_plan=self.weekly_plan
            )
            .select_related("work_center")
        )

        for capacity in weekly_capacities:

            work_center_id = (
                capacity.work_center_id
            )

            daily_capacity = (
                Decimal(capacity.headcount)
                * capacity.productive_hours_per_day
            )

            weekly_capacity = (
                daily_capacity
                * Decimal(capacity.working_days)
            )

            self.capacities[
                work_center_id
            ] = {
                "work_center":
                    capacity.work_center,

                "headcount":
                    capacity.headcount,

                "productive_hours_per_day":
                    capacity.productive_hours_per_day,

                "working_days":
                    capacity.working_days,

                "daily_capacity_mh":
                    daily_capacity,

                "weekly_capacity_mh":
                    weekly_capacity,

                "allocated_mh":
                    Decimal("0"),
            }

    def has_capacity_record(
        self,
        work_center
    ):
        """
        WorkCenter üçün həmin həftədə
        capacity məlumatının olub-olmadığını yoxlayır.
        """

        if work_center is None:
            return False

        return (
            work_center.id
            in self.capacities
        )

    def get_headcount(
        self,
        work_center
    ):
        """
        Həmin həftədə ekipin real adam sayını qaytarır.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return 0

        return self.capacities[
            work_center.id
        ]["headcount"]

    def get_daily_capacity_mh(
        self,
        work_center
    ):
        """
        WorkCenter-in gündəlik MH capacity-si.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return Decimal("0")

        return self.capacities[
            work_center.id
        ]["daily_capacity_mh"]

    def get_weekly_capacity_mh(
        self,
        work_center
    ):
        """
        WorkCenter-in həftəlik MH capacity-si.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return Decimal("0")

        return self.capacities[
            work_center.id
        ]["weekly_capacity_mh"]

    def get_allocated_mh(
        self,
        work_center
    ):
        """
        Scheduler tərəfindən artıq ayrılmış MH.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return Decimal("0")

        return self.capacities[
            work_center.id
        ]["allocated_mh"]

    def get_remaining_mh(
        self,
        work_center
    ):
        """
        Həftəlik qalan MH capacity.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return Decimal("0")

        data = self.capacities[
            work_center.id
        ]

        remaining = (
            data["weekly_capacity_mh"]
            - data["allocated_mh"]
        )

        return max(
            remaining,
            Decimal("0")
        )

    def can_allocate(
        self,
        work_center,
        required_people,
        planned_mh
    ):
        """
        Operation-un ilkin capacity yoxlaması.

        İki şərt:
        1. Operation üçün tələb olunan adam sayı
           ekipin real headcount-unu keçməməlidir.

        2. Operation-un MH-si həftəlik qalan
           MH-dan çox olmamalıdır.
        """

        if work_center is None:

            return (
                False,
                "Operation üçün WorkCenter yoxdur."
            )

        if not self.has_capacity_record(
            work_center
        ):

            return (
                False,
                (
                    f"{work_center.code} üçün "
                    f"{self.weekly_plan} həftəsində "
                    "capacity məlumatı yoxdur."
                )
            )

        if required_people is None:

            return (
                False,
                "Tələb olunan adam sayı yoxdur."
            )

        if planned_mh is None:

            return (
                False,
                "Planlanan MH yoxdur."
            )

        required_people = Decimal(
            str(required_people)
        )

        planned_mh = Decimal(
            str(planned_mh)
        )

        available_headcount = Decimal(
            self.get_headcount(
                work_center
            )
        )

        if required_people > available_headcount:

            return (
                False,
                (
                    f"Operation {required_people} nəfər "
                    f"tələb edir, lakin {work_center.code} "
                    f"ekipində yalnız "
                    f"{available_headcount} nəfər mövcuddur."
                )
            )

        remaining_mh = (
            self.get_remaining_mh(
                work_center
            )
        )

        if planned_mh > remaining_mh:

            return (
                False,
                (
                    f"Operation üçün {planned_mh} MH "
                    f"tələb olunur, lakin "
                    f"{work_center.code} üzrə "
                    f"yalnız {remaining_mh} MH "
                    "həftəlik capacity qalıb."
                )
            )

        return (
            True,
            "Capacity uyğundur."
        )

    def allocate(
        self,
        work_center,
        planned_mh
    ):
        """
        Operation scheduler tərəfindən qəbul edildikdə
        MH-ni ekip capacity-sindən istifadə olunmuş
        kimi qeyd edir.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return False

        planned_mh = Decimal(
            str(planned_mh)
        )

        remaining = self.get_remaining_mh(
            work_center
        )

        if planned_mh > remaining:
            return False

        self.capacities[
            work_center.id
        ]["allocated_mh"] += planned_mh

        return True

    def release(
        self,
        work_center,
        planned_mh
    ):
        """
        Planlanmış operation sonradan çıxarılsa,
        istifadə olunmuş capacity-ni geri qaytarır.
        """

        if not self.has_capacity_record(
            work_center
        ):
            return False

        planned_mh = Decimal(
            str(planned_mh)
        )

        current = self.capacities[
            work_center.id
        ]["allocated_mh"]

        new_value = (
            current - planned_mh
        )

        if new_value < Decimal("0"):
            new_value = Decimal("0")

        self.capacities[
            work_center.id
        ]["allocated_mh"] = new_value

        return True

    def get_utilization_percent(
        self,
        work_center
    ):
        """
        Ekip utilization faizini hesablayır.
        """

        weekly_capacity = (
            self.get_weekly_capacity_mh(
                work_center
            )
        )

        allocated = (
            self.get_allocated_mh(
                work_center
            )
        )

        if weekly_capacity <= 0:
            return Decimal("0")

        utilization = (
            allocated
            / weekly_capacity
            * Decimal("100")
        )

        return utilization.quantize(
            Decimal("0.01")
        )

    def get_summary(self):
        """
        Bütün WorkCenter-lər üzrə
        capacity xülasəsi.
        """

        results = []

        for work_center_id, data in (
            self.capacities.items()
        ):

            work_center = (
                data["work_center"]
            )

            weekly_capacity = (
                data["weekly_capacity_mh"]
            )

            allocated = (
                data["allocated_mh"]
            )

            remaining = (
                weekly_capacity - allocated
            )

            if remaining < 0:
                remaining = Decimal("0")

            if weekly_capacity > 0:

                utilization = (
                    allocated
                    / weekly_capacity
                    * Decimal("100")
                )

            else:
                utilization = Decimal("0")

            results.append(
                CapacityResult(
                    work_center_id=
                        work_center_id,

                    work_center_code=
                        work_center.code,

                    headcount=
                        data["headcount"],

                    productive_hours_per_day=
                        data[
                            "productive_hours_per_day"
                        ],

                    working_days=
                        data["working_days"],

                    daily_capacity_mh=
                        data["daily_capacity_mh"],

                    weekly_capacity_mh=
                        weekly_capacity,

                    allocated_mh=
                        allocated,

                    remaining_mh=
                        remaining,

                    utilization_percent=
                        utilization.quantize(
                            Decimal("0.01")
                        ),
                )
            )

        results.sort(
            key=lambda item:
                item.work_center_code
        )

        return results

class DailyCapacityTracker:
    """
    8.5 saatlıq scheduler üçün
    WorkCenter + tarix üzrə istifadə olunan
    adam-saatı izləyir.
    """

    def __init__(
        self,
        capacity_engine
    ):

        self.capacity_engine = (
            capacity_engine
        )

        self.daily_allocations = {}

    def _key(
        self,
        work_center,
        work_date
    ):

        return (
            work_center.id,
            work_date
        )

    def get_allocated_mh(
        self,
        work_center,
        work_date
    ):

        return self.daily_allocations.get(
            self._key(
                work_center,
                work_date
            ),
            Decimal("0")
        )

    def get_remaining_mh(
        self,
        work_center,
        work_date
    ):

        daily_capacity = (
            self.capacity_engine
            .get_daily_capacity_mh(
                work_center
            )
        )

        allocated = self.get_allocated_mh(
            work_center,
            work_date
        )

        remaining = (
            daily_capacity - allocated
        )

        return max(
            remaining,
            Decimal("0")
        )

    def can_allocate(
        self,
        work_center,
        work_date,
        planned_mh
    ):

        planned_mh = Decimal(
            str(planned_mh)
        )

        remaining = self.get_remaining_mh(
            work_center,
            work_date
        )

        return (
            planned_mh <= remaining
        )

    def allocate(
        self,
        work_center,
        work_date,
        planned_mh
    ):

        planned_mh = Decimal(
            str(planned_mh)
        )

        if not self.can_allocate(
            work_center,
            work_date,
            planned_mh
        ):
            return False

        key = self._key(
            work_center,
            work_date
        )

        current = (
            self.daily_allocations.get(
                key,
                Decimal("0")
            )
        )

        self.daily_allocations[
            key
        ] = (
            current + planned_mh
        )

        return True