from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from .models import WorkCalendarDay


class WorkCalendarService:
    """
    MPS üçün iş təqvimi servisi.

    Vəzifələri:
    1. İl üzrə baza təqvimini yaratmaq.
    2. Həftəsonlarını avtomatik qeyri-iş günü etmək.
    3. Rəsmi bayramları tətbiq etmək.
    4. Xüsusi iş / qeyri-iş günlərini override etmək.
    5. Scheduler üçün iş günü məlumatı vermək.

    Vacib:
    Manual override edilmiş tarixlər avtomatik
    generator tərəfindən dəyişdirilmir.
    """

    DEFAULT_PRODUCTIVE_HOURS = Decimal("6.75")

    # =====================================================
    # İL ÜZRƏ BAZA TƏQVİMİ
    # =====================================================

    @classmethod
    @transaction.atomic
    def generate_year(cls, year):
        """
        Verilmiş il üçün bütün tarixləri yaradır.

        Bazar ertəsi - Cümə:
            WORKING

        Şənbə - Bazar:
            WEEKEND

        Manual override edilmiş mövcud günlər
        dəyişdirilmir.
        """

        start_date = date(
            year,
            1,
            1
        )

        end_date = date(
            year,
            12,
            31
        )

        current_date = start_date

        created_count = 0
        updated_count = 0
        skipped_manual_count = 0

        while current_date <= end_date:

            existing = (
                WorkCalendarDay.objects
                .filter(
                    date=current_date
                )
                .first()
            )

            # Manual dəyişiklik varsa toxunmuruq.
            if (
                existing
                and existing.is_manual_override
            ):

                skipped_manual_count += 1

                current_date += timedelta(
                    days=1
                )

                continue

            # Şənbə / Bazar
            if current_date.weekday() >= 5:

                day_type = "WEEKEND"
                is_working_day = False
                working_hours = Decimal("0")

                name = (
                    "Həftəsonu"
                )

            # Bazar ertəsi / Cümə
            else:

                day_type = "WORKING"
                is_working_day = True

                working_hours = (
                    cls.DEFAULT_PRODUCTIVE_HOURS
                )

                name = (
                    "Normal iş günü"
                )

            _, created = (
                WorkCalendarDay.objects
                .update_or_create(
                    date=current_date,

                    defaults={
                        "day_type":
                            day_type,

                        "is_working_day":
                            is_working_day,

                        "name":
                            name,

                        "working_hours":
                            working_hours,

                        "source":
                            "MPS Base Calendar",

                        "is_manual_override":
                            False,
                    }
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            current_date += timedelta(
                days=1
            )

        return {
            "year": year,

            "created":
                created_count,

            "updated":
                updated_count,

            "manual_skipped":
                skipped_manual_count,
        }

    # =====================================================
    # TARİX ARALIĞI ÜZRƏ BAZA TƏQVİMİ
    # =====================================================

    @classmethod
    @transaction.atomic
    def generate_range(
        cls,
        start_date,
        end_date
    ):
        """
        Verilmiş tarix aralığında baza təqvimi yaradır.

        WeeklyPlan üçün də istifadə edilə bilər.
        """

        if start_date > end_date:

            raise ValueError(
                "Başlama tarixi bitmə "
                "tarixindən böyük ola bilməz."
            )

        current_date = start_date

        created_count = 0
        updated_count = 0
        skipped_manual_count = 0

        while current_date <= end_date:

            existing = (
                WorkCalendarDay.objects
                .filter(
                    date=current_date
                )
                .first()
            )

            if (
                existing
                and existing.is_manual_override
            ):

                skipped_manual_count += 1

                current_date += timedelta(
                    days=1
                )

                continue

            if current_date.weekday() >= 5:

                day_type = "WEEKEND"
                is_working_day = False
                working_hours = Decimal("0")
                name = "Həftəsonu"

            else:

                day_type = "WORKING"
                is_working_day = True

                working_hours = (
                    cls.DEFAULT_PRODUCTIVE_HOURS
                )

                name = "Normal iş günü"

            _, created = (
                WorkCalendarDay.objects
                .update_or_create(
                    date=current_date,

                    defaults={
                        "day_type":
                            day_type,

                        "is_working_day":
                            is_working_day,

                        "name":
                            name,

                        "working_hours":
                            working_hours,

                        "source":
                            "MPS Base Calendar",

                        "is_manual_override":
                            False,
                    }
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

            current_date += timedelta(
                days=1
            )

        return {
            "created":
                created_count,

            "updated":
                updated_count,

            "manual_skipped":
                skipped_manual_count,
        }

    # =====================================================
    # RƏSMİ BAYRAM / QEYRİ-İŞ GÜNÜ
    # =====================================================

    @classmethod
    def set_holiday(
        cls,
        work_date,
        name,
        source="Official Calendar",
        manual=False,
    ):
        """
        Tarixi rəsmi bayram / qeyri-iş günü edir.
        """

        calendar_day, _ = (
            WorkCalendarDay.objects
            .update_or_create(
                date=work_date,

                defaults={
                    "day_type":
                        "HOLIDAY",

                    "is_working_day":
                        False,

                    "name":
                        name,

                    "working_hours":
                        Decimal("0"),

                    "source":
                        source,

                    "is_manual_override":
                        manual,
                }
            )
        )

        return calendar_day

    # =====================================================
    # XÜSUSİ QEYRİ-İŞ GÜNÜ
    # =====================================================

    @classmethod
    def set_non_working_day(
        cls,
        work_date,
        name="Qeyri-iş günü",
        source="Manual",
    ):
        """
        Normal iş gününü xüsusi səbəbdən
        qeyri-iş gününə çevirir.
        """

        calendar_day, _ = (
            WorkCalendarDay.objects
            .update_or_create(
                date=work_date,

                defaults={
                    "day_type":
                        "NON_WORKING",

                    "is_working_day":
                        False,

                    "name":
                        name,

                    "working_hours":
                        Decimal("0"),

                    "source":
                        source,

                    "is_manual_override":
                        True,
                }
            )
        )

        return calendar_day

    # =====================================================
    # XÜSUSİ İŞ GÜNÜ
    # =====================================================

    @classmethod
    def set_special_working_day(
        cls,
        work_date,
        name="Xüsusi iş günü",
        working_hours=Decimal("6.75"),
        source="Manual",
    ):
        """
        Şənbə, bazar və ya başqa qeyri-iş gününü
        xüsusi iş gününə çevirir.
        """

        calendar_day, _ = (
            WorkCalendarDay.objects
            .update_or_create(
                date=work_date,

                defaults={
                    "day_type":
                        "SPECIAL_WORKING",

                    "is_working_day":
                        True,

                    "name":
                        name,

                    "working_hours":
                        Decimal(
                            str(working_hours)
                        ),

                    "source":
                        source,

                    "is_manual_override":
                        True,
                }
            )
        )

        return calendar_day

    # =====================================================
    # NORMAL GÜNƏ QAYTAR
    # =====================================================

    @classmethod
    def reset_day(
        cls,
        work_date
    ):
        """
        Manual dəyişdirilmiş günü yenidən
        həftənin normal qaydasına qaytarır.
        """

        if work_date.weekday() >= 5:

            defaults = {
                "day_type":
                    "WEEKEND",

                "is_working_day":
                    False,

                "name":
                    "Həftəsonu",

                "working_hours":
                    Decimal("0"),

                "source":
                    "MPS Base Calendar",

                "is_manual_override":
                    False,
            }

        else:

            defaults = {
                "day_type":
                    "WORKING",

                "is_working_day":
                    True,

                "name":
                    "Normal iş günü",

                "working_hours":
                    cls.DEFAULT_PRODUCTIVE_HOURS,

                "source":
                    "MPS Base Calendar",

                "is_manual_override":
                    False,
            }

        calendar_day, _ = (
            WorkCalendarDay.objects
            .update_or_create(
                date=work_date,
                defaults=defaults
            )
        )

        return calendar_day

    # =====================================================
    # İŞ GÜNÜDÜRMÜ?
    # =====================================================

    @classmethod
    def is_working_day(
        cls,
        work_date
    ):
        """
        Scheduler-in istifadə edəcəyi əsas metod.

        Təqvimdə tarix varsa database qərarı əsasdır.

        Tarix bazada yoxdursa fallback:
        B.e.-Cümə = iş günü
        Şənbə-Bazar = qeyri-iş günü
        """

        calendar_day = (
            WorkCalendarDay.objects
            .filter(
                date=work_date
            )
            .first()
        )

        if calendar_day:

            return (
                calendar_day.is_working_day
            )

        return (
            work_date.weekday() < 5
        )

    # =====================================================
    # GÜNLÜK MƏHSULDAR SAAT
    # =====================================================

    @classmethod
    def get_working_hours(
        cls,
        work_date
    ):
        """
        Verilmiş tarix üçün məhsuldar iş saatını qaytarır.
        """

        calendar_day = (
            WorkCalendarDay.objects
            .filter(
                date=work_date
            )
            .first()
        )

        if calendar_day:

            if not calendar_day.is_working_day:
                return Decimal("0")

            return (
                calendar_day.working_hours
            )

        if work_date.weekday() < 5:

            return (
                cls.DEFAULT_PRODUCTIVE_HOURS
            )

        return Decimal("0")

    # =====================================================
    # İŞ GÜNLƏRİNİ QAYTAR
    # =====================================================

    @classmethod
    def get_working_days(
        cls,
        start_date,
        end_date
    ):
        """
        Tarix aralığındakı bütün iş günlərini qaytarır.
        """

        result = []

        current_date = start_date

        while current_date <= end_date:

            if cls.is_working_day(
                current_date
            ):

                result.append(
                    current_date
                )

            current_date += timedelta(
                days=1
            )

        return result

    # =====================================================
    # İŞ GÜNÜ SAYI
    # =====================================================

    @classmethod
    def count_working_days(
        cls,
        start_date,
        end_date
    ):

        return len(
            cls.get_working_days(
                start_date,
                end_date
            )
        )

    # =====================================================
    # NÖVBƏTİ İŞ GÜNÜ
    # =====================================================

    @classmethod
    def next_working_day(
        cls,
        work_date
    ):
        """
        Verilmiş tarixdən sonrakı
        ilk iş gününü qaytarır.
        """

        current_date = (
            work_date
            + timedelta(days=1)
        )

        while not cls.is_working_day(
            current_date
        ):

            current_date += timedelta(
                days=1
            )

        return current_date

    # =====================================================
    # ƏVVƏLKİ İŞ GÜNÜ
    # =====================================================

    @classmethod
    def previous_working_day(
        cls,
        work_date
    ):

        current_date = (
            work_date
            - timedelta(days=1)
        )

        while not cls.is_working_day(
            current_date
        ):

            current_date -= timedelta(
                days=1
            )

        return current_date

    # =====================================================
    # AY ÜZRƏ STATİSTİKA
    # =====================================================

    @classmethod
    def month_summary(
        cls,
        year,
        month
    ):
        """
        Ay üzrə iş / qeyri-iş günü statistikasını verir.
        """

        days_in_month = (
            monthrange(
                year,
                month
            )[1]
        )

        working_days = 0
        non_working_days = 0

        total_productive_hours = (
            Decimal("0")
        )

        for day_number in range(
            1,
            days_in_month + 1
        ):

            work_date = date(
                year,
                month,
                day_number
            )

            if cls.is_working_day(
                work_date
            ):

                working_days += 1

                total_productive_hours += (
                    cls.get_working_hours(
                        work_date
                    )
                )

            else:

                non_working_days += 1

        return {
            "year":
                year,

            "month":
                month,

            "working_days":
                working_days,

            "non_working_days":
                non_working_days,

            "total_productive_hours":
                total_productive_hours,
        }