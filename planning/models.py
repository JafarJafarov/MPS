from django.db import models


# =========================================================
# WEEKLY PLAN
# =========================================================

class WeeklyPlan(models.Model):

    STATUS_CHOICES = [
        ("DRAFT", "Hazırlanır"),
        ("SCHEDULED", "Proqram hazırlanıb"),
        ("APPROVED", "Təsdiqlənib"),
        ("CLOSED", "Bağlanıb"),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name="Proqramın adı"
    )

    week_number = models.PositiveSmallIntegerField(
        verbose_name="Həftə nömrəsi"
    )

    year = models.PositiveSmallIntegerField(
        verbose_name="İl"
    )

    start_date = models.DateField(
        verbose_name="Başlama tarixi"
    )

    end_date = models.DateField(
        verbose_name="Bitmə tarixi"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
        verbose_name="Status"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "-year",
            "-week_number"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "year",
                    "week_number"
                ],
                name="unique_year_week"
            )
        ]

    def __str__(self):

        return (
            f"W{self.week_number}-"
            f"{self.year}"
        )


# =========================================================
# SAP ORDER
# =========================================================

class SAPOrder(models.Model):

    order_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name="Sifariş nömrəsi"
    )

    priority = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Prioritet"
    )

    order_type = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Sifariş tipi"
    )

    created_on = models.DateField(
        null=True,
        blank=True,
        verbose_name="Yaranma tarixi"
    )

    system_status = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Sistem statusu"
    )

    revision = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Revision"
    )

    imported_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Sistemə yüklənmə vaxtı"
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "order_number"
        ]

        verbose_name = (
            "SAP sifarişi"
        )

        verbose_name_plural = (
            "SAP sifarişləri"
        )

    def __str__(self):

        return self.order_number


# =========================================================
# SAP OPERATION
# =========================================================

class SAPOperation(models.Model):

    order = models.ForeignKey(
        SAPOrder,
        on_delete=models.CASCADE,
        related_name="operations",
        verbose_name="Sifariş"
    )

    operation_number = models.CharField(
        max_length=20,
        verbose_name="Operation nömrəsi"
    )

    work_center = models.ForeignKey(
        "capacity.WorkCenter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sap_operations",
        verbose_name="İcra edən ekip"
    )

    work_center_code_raw = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="SAP-dakı ekip kodu"
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="İşin təsviri"
    )

    required_people = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tələb olunan adam sayı"
    )

    planned_work_mh = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Planlanan adam-saat"
    )

    actual_work_mh = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Faktiki adam-saat"
    )

    operation_system_status = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Operation sistem statusu"
    )

    user_status = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="İstifadəçi statusu"
    )

    maintenance_activity_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Təmir fəaliyyət tipi"
    )

    revision = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Operation Revision"
    )

    imported_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "order__order_number",
            "operation_number"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "order",
                    "operation_number"
                ],
                name="unique_order_operation"
            )
        ]

        verbose_name = (
            "SAP operation"
        )

        verbose_name_plural = (
            "SAP operation-ları"
        )

    @property
    def calculated_duration_hours(self):

        if (
            self.planned_work_mh is not None
            and self.required_people is not None
            and self.required_people > 0
        ):

            return (
                self.planned_work_mh
                / self.required_people
            )

        return None

    def __str__(self):

        return (
            f"{self.order.order_number} / "
            f"{self.operation_number}"
        )


# =========================================================
# ITK REQUEST
# =========================================================

class ITKRequest(models.Model):
    """
    İTK tərəfindən konkret həftənin
    təmir proqramına daxil edilməsi
    tələb olunan SAP sifarişi.
    """

    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="itk_requests",
        verbose_name="Proqram həftəsi"
    )

    order_number = models.CharField(
        max_length=30,
        db_index=True,
        verbose_name="SAP sifariş nömrəsi"
    )

    note = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="İTK qeydi"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "weekly_plan",
            "order_number"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "weekly_plan",
                    "order_number"
                ],
                name="unique_itk_order_per_week"
            )
        ]

        verbose_name = (
            "İTK proqram tələbi"
        )

        verbose_name_plural = (
            "İTK proqram tələbləri"
        )

    @property
    def sap_order(self):
        """
        İTK sifarişinin SAP bazasında
        olub-olmadığını yoxlayır.
        """

        return (
            SAPOrder.objects
            .filter(
                order_number=self.order_number
            )
            .first()
        )

    @property
    def exists_in_sap(self):

        return (
            self.sap_order is not None
        )

    def __str__(self):

        return (
            f"{self.weekly_plan} | "
            f"{self.order_number}"
        )


# =========================================================
# WORK CALENDAR DAY
# =========================================================

class WorkCalendarDay(models.Model):
    """
    MPS iş təqvimi.

    Hər tarix üçün həmin günün:
    - normal iş günü,
    - həftəsonu,
    - rəsmi bayram,
    - qeyri-iş günü,
    - xüsusi iş günü

    olması burada saxlanılır.

    Scheduler gələcəkdə planlama zamanı
    bu cədvələ baxacaq.
    """

    DAY_TYPE_CHOICES = [

        (
            "WORKING",
            "İş günü"
        ),

        (
            "WEEKEND",
            "Həftəsonu"
        ),

        (
            "HOLIDAY",
            "Rəsmi bayram"
        ),

        (
            "NON_WORKING",
            "Qeyri-iş günü"
        ),

        (
            "SPECIAL_WORKING",
            "Xüsusi iş günü"
        ),
    ]

    date = models.DateField(
        unique=True,
        db_index=True,
        verbose_name="Tarix"
    )

    day_type = models.CharField(
        max_length=20,
        choices=DAY_TYPE_CHOICES,
        default="WORKING",
        db_index=True,
        verbose_name="Günün tipi"
    )

    is_working_day = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="İş günüdür"
    )

    name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Günün adı / qeyd"
    )

    working_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=6.75,
        verbose_name="Məhsuldar iş saatı"
    )

    source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Məlumat mənbəyi"
    )

    is_manual_override = models.BooleanField(
        default=False,
        verbose_name="Manual dəyişiklik"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "date"
        ]

        indexes = [
            models.Index(
                fields=[
                    "date",
                    "is_working_day"
                ]
            )
        ]

        verbose_name = (
            "İş təqvimi günü"
        )

        verbose_name_plural = (
            "İş təqvimi günləri"
        )

    @property
    def weekday_name(self):

        names = {
            0: "Bazar ertəsi",
            1: "Çərşənbə axşamı",
            2: "Çərşənbə",
            3: "Cümə axşamı",
            4: "Cümə",
            5: "Şənbə",
            6: "Bazar",
        }

        return names.get(
            self.date.weekday(),
            ""
        )

    def __str__(self):

        return (
            f"{self.date:%d.%m.%Y} | "
            f"{self.get_day_type_display()}"
        )