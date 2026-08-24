from django.db import models

from planning.models import (
    WeeklyPlan,
    SAPOperation,
)

from capacity.models import WorkCenter


# =========================================================
# SCHEDULED OPERATION
# =========================================================

class ScheduledOperation(models.Model):
    """
    Scheduling Engine-in hər SAP operation-u üçün
    verdiyi yekun planlama qərarını saxlayır.

    Operation:
    - proqrama alına bilər,
    - proqrama alınmaya bilər,
    - manual review tələb edə bilər.
    """

    DECISION_CHOICES = [
        (
            "SCHEDULED",
            "Proqrama alındı"
        ),
        (
            "NOT_SCHEDULED",
            "Proqrama alınmadı"
        ),
        (
            "REVIEW",
            "Manual yoxlama tələb olunur"
        ),
    ]

    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="scheduled_operations",
        verbose_name="Həftəlik proqram"
    )

    sap_operation = models.ForeignKey(
        SAPOperation,
        on_delete=models.CASCADE,
        related_name="schedule_results",
        verbose_name="SAP Operation"
    )

    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_operations",
        verbose_name="Planlanan ekip"
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        default="REVIEW",
        db_index=True,
        verbose_name="Planlama qərarı"
    )

    decision_reason = models.TextField(
        blank=True,
        verbose_name="Qərarın səbəbi"
    )

    priority = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Prioritet"
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Due Date"
    )

    is_overdue = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Gecikmiş iş"
    )

    scheduled_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Planlanan başlanğıc tarixi"
    )

    scheduled_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Başlama saatı"
    )

    scheduled_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Son segmentin bitmə saatı"
    )

    required_people = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Tələb olunan adam sayı"
    )

    planned_mh = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Planlanan adam-saat"
    )

    planned_duration_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Planlanan müddət, saat"
    )

    sequence = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Planlama ardıcıllığı"
    )

    scheduler_score = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Scheduler balı"
    )

    is_locked = models.BooleanField(
        default=False,
        verbose_name="Manual kilidlənib"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "scheduled_date",
            "scheduled_start",
            "sequence",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "weekly_plan",
                    "sap_operation",
                ],
                name=(
                    "unique_operation_per_week_schedule"
                )
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "weekly_plan",
                    "decision",
                ]
            ),

            models.Index(
                fields=[
                    "weekly_plan",
                    "work_center",
                    "scheduled_date",
                ]
            ),
        ]

        verbose_name = (
            "Planlanmış operation"
        )

        verbose_name_plural = (
            "Planlanmış operation-lar"
        )

    @property
    def order_number(self):

        return (
            self.sap_operation
            .order
            .order_number
        )

    @property
    def operation_number(self):

        return (
            self.sap_operation
            .operation_number
        )

    def __str__(self):

        return (
            f"{self.weekly_plan} | "
            f"{self.order_number} / "
            f"{self.operation_number}"
        )


# =========================================================
# SCHEDULE SEGMENT
# =========================================================

class ScheduleSegment(models.Model):
    """
    Bir planlanmış operation-un faktiki
    iş intervallarını saxlayır.

    Misal:

    08:00 - 12:00
    13:00 - 15:45

    Bunlar eyni operation-un iki ayrı
    ScheduleSegment-i olacaq.

    Operation növbəti günə keçərsə,
    həmin gün üçün də ayrıca segment yaranacaq.
    """

    scheduled_operation = models.ForeignKey(
        ScheduledOperation,
        on_delete=models.CASCADE,
        related_name="segments",
        verbose_name="Planlanmış operation"
    )

    work_date = models.DateField(
        db_index=True,
        verbose_name="İş tarixi"
    )

    start_time = models.TimeField(
        verbose_name="Başlama saatı"
    )

    end_time = models.TimeField(
        verbose_name="Bitmə saatı"
    )

    required_people = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Adam sayı"
    )

    segment_mh = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Segment MH"
    )

    sequence = models.PositiveIntegerField(
        default=1,
        verbose_name="Segment ardıcıllığı"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "work_date",
            "start_time",
            "sequence",
        ]

        indexes = [
            models.Index(
                fields=[
                    "work_date",
                    "start_time",
                ]
            )
        ]

        verbose_name = (
            "Schedule segment"
        )

        verbose_name_plural = (
            "Schedule segmentləri"
        )

    @property
    def duration_hours(self):
        """
        Segmentin real müddətini saatla qaytarır.
        """

        from datetime import datetime

        start = datetime.combine(
            self.work_date,
            self.start_time
        )

        end = datetime.combine(
            self.work_date,
            self.end_time
        )

        seconds = (
            end - start
        ).total_seconds()

        return (
            seconds / 3600
        )

    def __str__(self):

        return (
            f"{self.scheduled_operation} | "
            f"{self.work_date} | "
            f"{self.start_time}-"
            f"{self.end_time}"
        )


# =========================================================
# SCHEDULING RUN
# =========================================================

class SchedulingRun(models.Model):
    """
    Scheduling Engine-in hər işə salınmasını saxlayır.

    Bununla:
    - scheduler nə vaxt işləyib,
    - neçə operation yoxlanılıb,
    - neçəsi proqrama alınıb,
    - neçəsi alınmayıb,
    - neçə MH planlanıb

    izləyə biləcəyik.
    """

    STATUS_CHOICES = [
        (
            "RUNNING",
            "Hesablanır"
        ),
        (
            "COMPLETED",
            "Tamamlandı"
        ),
        (
            "FAILED",
            "Xəta"
        ),
    ]

    weekly_plan = models.ForeignKey(
        WeeklyPlan,
        on_delete=models.CASCADE,
        related_name="scheduling_runs",
        verbose_name="Həftəlik proqram"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="RUNNING",
        db_index=True,
        verbose_name="Status"
    )

    total_operations = models.PositiveIntegerField(
        default=0,
        verbose_name="Ümumi operation"
    )

    scheduled_operations = models.PositiveIntegerField(
        default=0,
        verbose_name="Proqrama alınan"
    )

    not_scheduled_operations = (
        models.PositiveIntegerField(
            default=0,
            verbose_name="Proqrama alınmayan"
        )
    )

    review_operations = models.PositiveIntegerField(
        default=0,
        verbose_name="Manual review"
    )

    total_planned_mh = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Ümumi plan MH"
    )

    error_message = models.TextField(
        blank=True,
        verbose_name="Xəta məlumatı"
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Başlama vaxtı"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bitmə vaxtı"
    )

    class Meta:

        ordering = [
            "-started_at"
        ]

        verbose_name = (
            "Scheduling Run"
        )

        verbose_name_plural = (
            "Scheduling Run-lar"
        )

    def __str__(self):

        return (
            f"{self.weekly_plan} | "
            f"{self.status} | "
            f"{self.started_at:%d.%m.%Y %H:%M}"
        )