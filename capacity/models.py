from django.db import models


class WorkCenter(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="WorkCenter"
    )

    name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Ekip adı"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "Ekip"
        verbose_name_plural = "Ekiplər"

    def __str__(self):
        return self.code


class WeeklyCapacity(models.Model):

    weekly_plan = models.ForeignKey(
        "planning.WeeklyPlan",
        on_delete=models.CASCADE,
        related_name="weekly_capacities",
        verbose_name="Həftəlik proqram"
    )

    work_center = models.ForeignKey(
        WorkCenter,
        on_delete=models.PROTECT,
        related_name="capacity_history",
        verbose_name="WorkCenter"
    )

    headcount = models.PositiveIntegerField(
        verbose_name="Mövcud adam sayı"
    )

    productive_hours_per_day = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=6.75,
        verbose_name="Məhsuldar saat / gün"
    )

    working_days = models.PositiveSmallIntegerField(
        default=5,
        verbose_name="İş günü sayı"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = [
            "-weekly_plan__year",
            "-weekly_plan__week_number",
            "work_center__code"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "weekly_plan",
                    "work_center"
                ],
                name="unique_week_workcenter_capacity"
            )
        ]

        verbose_name = "Həftəlik kapasite"
        verbose_name_plural = "Həftəlik kapasitələr"

    @property
    def daily_capacity_mh(self):
        return (
            self.headcount
            * self.productive_hours_per_day
        )

    @property
    def weekly_capacity_mh(self):
        return (
            self.headcount
            * self.productive_hours_per_day
            * self.working_days
        )

    def __str__(self):
        return (
            f"{self.weekly_plan} | "
            f"{self.work_center.code} | "
            f"{self.headcount} nəfər"
        )