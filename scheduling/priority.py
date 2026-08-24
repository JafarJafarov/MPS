from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from planning.models import SAPOperation


@dataclass
class PriorityResult:
    """
    Operation üçün Priority Engine nəticəsi.
    """

    priority: Optional[int]
    creation_date: Optional[date]
    due_date: Optional[date]

    is_overdue: bool
    overdue_days: int

    days_to_due: Optional[int]

    score: float

    code: str
    reason: str


class PriorityEngine:
    """
    SAP operation-larının prioritetini,
    due date-ni və scheduling ardıcıllığını hesablayır.
    """

    PRIORITY_DAYS = {
        1: 0,
        2: 7,
        3: 14,
        4: 30,
        5: 60,
    }

    def calculate(
        self,
        operation: SAPOperation,
        reference_date: date
    ) -> PriorityResult:

        order = operation.order

        priority = order.priority
        creation_date = order.created_on

        # -----------------------------------
        # 1. Priority yoxlanması
        # -----------------------------------

        if priority not in self.PRIORITY_DAYS:

            return PriorityResult(
                priority=priority,
                creation_date=creation_date,
                due_date=None,
                is_overdue=False,
                overdue_days=0,
                days_to_due=None,
                score=0,
                code="INVALID_PRIORITY",
                reason=(
                    "Sifariş üçün etibarlı "
                    "1-5 prioriteti yoxdur."
                )
            )

        # -----------------------------------
        # 2. Creation Date yoxlanması
        # -----------------------------------

        if creation_date is None:

            return PriorityResult(
                priority=priority,
                creation_date=None,
                due_date=None,
                is_overdue=False,
                overdue_days=0,
                days_to_due=None,
                score=0,
                code="NO_CREATION_DATE",
                reason=(
                    "Sifarişin yaranma tarixi yoxdur. "
                    "Due Date hesablana bilmədi."
                )
            )

        # -----------------------------------
        # 3. Due Date hesablanması
        # -----------------------------------

        additional_days = (
            self.PRIORITY_DAYS[priority]
        )

        due_date = (
            creation_date
            + timedelta(days=additional_days)
        )

        # -----------------------------------
        # 4. Gecikmə hesablanması
        # -----------------------------------

        difference = (
            due_date - reference_date
        ).days

        if difference < 0:

            is_overdue = True
            overdue_days = abs(difference)
            days_to_due = difference

        else:

            is_overdue = False
            overdue_days = 0
            days_to_due = difference

        # -----------------------------------
        # 5. Scheduler score
        # -----------------------------------

        score = self._calculate_score(
            priority=priority,
            is_overdue=is_overdue,
            overdue_days=overdue_days,
            days_to_due=days_to_due,
        )

        # -----------------------------------
        # 6. İzah
        # -----------------------------------

        if is_overdue:

            reason = (
                f"P{priority} sifariş. "
                f"Due Date: "
                f"{due_date.strftime('%d.%m.%Y')}. "
                f"{overdue_days} gün gecikib."
            )

            code = "OVERDUE"

        elif days_to_due == 0:

            reason = (
                f"P{priority} sifariş. "
                "Due Date bu gündür."
            )

            code = "DUE_TODAY"

        else:

            reason = (
                f"P{priority} sifariş. "
                f"Due Date: "
                f"{due_date.strftime('%d.%m.%Y')}. "
                f"Due Date-ə {days_to_due} gün qalır."
            )

            code = "ACTIVE"

        return PriorityResult(
            priority=priority,
            creation_date=creation_date,
            due_date=due_date,
            is_overdue=is_overdue,
            overdue_days=overdue_days,
            days_to_due=days_to_due,
            score=score,
            code=code,
            reason=reason,
        )

    def _calculate_score(
        self,
        priority: int,
        is_overdue: bool,
        overdue_days: int,
        days_to_due: int,
    ) -> float:
        """
        Böyük score = daha yüksək scheduling üstünlüyü.

        Score yalnız sıralamanı asanlaşdırmaq üçündür.
        Əsas biznes qaydaları ayrıca sort key-də də qorunur.
        """

        priority_score = {
            1: 5000,
            2: 4000,
            3: 3000,
            4: 2000,
            5: 1000,
        }[priority]

        score = float(priority_score)

        if is_overdue:
            score += 10000
            score += min(
                overdue_days * 10,
                5000
            )

        else:
            urgency_bonus = max(
                0,
                1000 - (days_to_due * 10)
            )

            score += urgency_bonus

        return score

def prioritize_operations(
    operations,
    reference_date
):
    """
    Operation-ları scheduling ardıcıllığına salır.

    Ardıcıllıq:
    1. Gecikmiş işlər
    2. Due Date daha erkən olan
    3. Daha yüksək prioritet
    4. Daha köhnə Creation Date
    5. Order və Operation nömrəsi
    """

    engine = PriorityEngine()

    results = []

    for operation in operations:

        result = engine.calculate(
            operation=operation,
            reference_date=reference_date
        )

        results.append({
            "operation": operation,
            "priority_result": result,
        })

    def sort_key(item):

        operation = item["operation"]
        result = item["priority_result"]

        # Due Date olmayan işi axıra atırıq.
        due_date = (
            result.due_date
            or date.max
        )

        priority = (
            result.priority
            if result.priority in {1, 2, 3, 4, 5}
            else 999
        )

        creation_date = (
            result.creation_date
            or date.max
        )

        overdue_rank = (
            0 if result.is_overdue else 1
        )

        return (
            overdue_rank,
            due_date,
            priority,
            creation_date,
            operation.order.order_number,
            operation.operation_number,
        )

    results.sort(
        key=sort_key
    )

    # Son ardıcıllıq nömrəsi
    for sequence, item in enumerate(
        results,
        start=1
    ):
        item["sequence"] = sequence

    return results