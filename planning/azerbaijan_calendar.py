from datetime import date

from .calendar_service import WorkCalendarService


class AzerbaijanCalendar2026:
    """
    Azərbaycan Respublikasının 2026-cı il üzrə
    rəsmi istehsalat təqviminin MPS-ə tətbiqi.

    Rejim:
        5 günlük iş həftəsi

    Mənbə:
        Azərbaycan Respublikası Əmək və Əhalinin
        Sosial Müdafiəsi Nazirliyinin
        2026-cı il istehsalat təqvimi.
    """

    SOURCE = (
        "ƏƏSMN - 2026 İstehsalat Təqvimi"
    )

    # =====================================================
    # RƏSMİ BAYRAM / QEYRİ-İŞ GÜNLƏRİ
    # =====================================================

    HOLIDAYS = [

        # Yeni il
        (
            date(2026, 1, 1),
            "Yeni il bayramı"
        ),
        (
            date(2026, 1, 2),
            "Yeni il bayramı"
        ),

        # 20 Yanvar
        (
            date(2026, 1, 20),
            "Ümumxalq Hüzn Günü"
        ),

        # 8 Mart
        (
            date(2026, 3, 8),
            "Qadınlar Günü"
        ),

        # Novruz
        (
            date(2026, 3, 20),
            "Novruz bayramı"
        ),
        (
            date(2026, 3, 21),
            "Novruz bayramı"
        ),
        (
            date(2026, 3, 22),
            "Novruz bayramı"
        ),
        (
            date(2026, 3, 23),
            "Novruz bayramı"
        ),
        (
            date(2026, 3, 24),
            "Novruz bayramı"
        ),

        # Ramazan
        (
            date(2026, 3, 20),
            "Novruz / Ramazan bayramı"
        ),
        (
            date(2026, 3, 21),
            "Novruz / Ramazan bayramı"
        ),

        # 9 May
        (
            date(2026, 5, 9),
            "Faşizm üzərində Qələbə Günü"
        ),

        # Qurban
        (
            date(2026, 5, 27),
            "Qurban bayramı"
        ),
        (
            date(2026, 5, 28),
            "Qurban bayramı / Müstəqillik Günü"
        ),

        # 28 May
        (
            date(2026, 5, 28),
            "Qurban bayramı / Müstəqillik Günü"
        ),

        # 15 İyun
        (
            date(2026, 6, 15),
            "Milli Qurtuluş Günü"
        ),

        # 26 İyun
        (
            date(2026, 6, 26),
            "Silahlı Qüvvələr Günü"
        ),

        # 8 Noyabr
        (
            date(2026, 11, 8),
            "Zəfər Günü"
        ),

        # 9 Noyabr
        (
            date(2026, 11, 9),
            "Dövlət Bayrağı Günü"
        ),

        # 31 Dekabr
        (
            date(2026, 12, 31),
            "Dünya Azərbaycanlılarının "
            "Həmrəyliyi Günü"
        ),
    ]

    # =====================================================
    # ƏLAVƏ İSTİRAHƏT GÜNLƏRİ
    # =====================================================
    #
    # 2026-cı ilin rəsmi istehsalat təqviminə əsasən
    # 5 günlük iş həftəsi üçün.
    # =====================================================

    ADDITIONAL_NON_WORKING_DAYS = [

        (
            date(2026, 3, 9),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 3, 25),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 3, 26),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 3, 27),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 3, 30),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 5, 11),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 5, 29),
            "Əlavə istirahət günü"
        ),

        (
            date(2026, 11, 10),
            "Əlavə istirahət günü"
        ),
    ]

    # =====================================================
    # TƏQVİMİ TƏTBİQ ET
    # =====================================================

    @classmethod
    def apply(cls):
        """
        2026 baza təqvimini yaradır və sonra
        Azərbaycanın rəsmi qeyri-iş günlərini tətbiq edir.
        """

        result = (
            WorkCalendarService.generate_year(
                2026
            )
        )

        holiday_count = 0
        additional_count = 0

        # ---------------------------------------------
        # Rəsmi bayramlar
        # ---------------------------------------------

        for (
            holiday_date,
            holiday_name
        ) in cls.HOLIDAYS:

            WorkCalendarService.set_holiday(
                work_date=holiday_date,
                name=holiday_name,
                source=cls.SOURCE,
                manual=True,
            )

            holiday_count += 1

        # ---------------------------------------------
        # Əlavə istirahət günləri
        # ---------------------------------------------

        for (
            non_working_date,
            non_working_name
        ) in cls.ADDITIONAL_NON_WORKING_DAYS:

            WorkCalendarService.set_non_working_day(
                work_date=non_working_date,
                name=non_working_name,
                source=cls.SOURCE,
            )

            additional_count += 1

        return {
            "year": 2026,
            "base_calendar": result,
            "holidays_applied": holiday_count,
            "additional_days_applied": additional_count,
        }