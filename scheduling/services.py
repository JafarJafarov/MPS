from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from planning.models import SAPOperation


@dataclass
class EligibilityResult:
    """
    Bir SAP operation-un scheduling üçün
    uyğunluq nəticəsi.
    """

    eligible: bool
    code: str
    reason: str
    severity: str = "BLOCK"


class EligibilityEngine:
    """
    SAP operation-larını Scheduling Engine-ə
    buraxmazdan əvvəl yoxlayan filter engine.
    """

    BLOCKING_STATUS_CODES = {
        "MATG": "Material mövcud deyil",
        "OPEG": "İstehsalat işi icraya verə bilmir",
    }

    def check(
        self,
        operation: SAPOperation
    ) -> EligibilityResult:

        # ---------------------------------
        # 1. SAP operation mövcuddur?
        # ---------------------------------

        if operation is None:
            return EligibilityResult(
                eligible=False,
                code="NO_OPERATION",
                reason="SAP operation tapılmadı."
            )

        # ---------------------------------
        # 2. Bloklayıcı statusların yoxlanması
        # ---------------------------------

        status_result = self._check_blocking_status(
            operation
        )

        if status_result is not None:
            return status_result

        # ---------------------------------
        # 3. WorkCenter yoxlanması
        # ---------------------------------

        workcenter_result = self._check_workcenter(
            operation
        )

        if workcenter_result is not None:
            return workcenter_result

        # ---------------------------------
        # 4. Adam sayı yoxlanması
        # ---------------------------------

        people_result = self._check_required_people(
            operation
        )

        if people_result is not None:
            return people_result

        # ---------------------------------
        # 5. Plan MH yoxlanması
        # ---------------------------------

        mh_result = self._check_planned_mh(
            operation
        )

        if mh_result is not None:
            return mh_result

        # ---------------------------------
        # Bütün yoxlamalardan keçdi
        # ---------------------------------

        return EligibilityResult(
            eligible=True,
            code="ELIGIBLE",
            reason=(
                "Operation scheduling üçün uyğundur."
            ),
            severity="OK"
        )

    def _check_blocking_status(
        self,
        operation: SAPOperation
    ) -> Optional[EligibilityResult]:

        status_fields = [
            operation.operation_system_status,
            operation.user_status,
        ]

        combined_status = " ".join(
            str(value).upper()
            for value in status_fields
            if value
        )

        for code, description in (
            self.BLOCKING_STATUS_CODES.items()
        ):

            if code in combined_status:

                return EligibilityResult(
                    eligible=False,
                    code=code,
                    reason=(
                        f"{code}: {description}. "
                        "Operation avtomatik olaraq "
                        "proqramdan çıxarıldı."
                    )
                )

        return None

    def _check_workcenter(
        self,
        operation: SAPOperation
    ) -> Optional[EligibilityResult]:

        if operation.work_center is not None:
            return None

        raw_code = (
            operation.work_center_code_raw
            or ""
        ).strip()

        if not raw_code:
            return EligibilityResult(
                eligible=False,
                code="NO_WORKCENTER",
                reason=(
                    "Operation üçün WorkCenter "
                    "məlumatı yoxdur."
                )
            )

        return EligibilityResult(
            eligible=False,
            code="WORKCENTER_NOT_MAPPED",
            reason=(
                f"SAP WorkCenter '{raw_code}' "
                "sistemdə master ekip siyahısına "
                "bağlanmayıb."
            )
        )

    def _check_required_people(
        self,
        operation: SAPOperation
    ) -> Optional[EligibilityResult]:

        people = operation.required_people

        if people is None:
            return EligibilityResult(
                eligible=False,
                code="NO_REQUIRED_PEOPLE",
                reason=(
                    "Operation üçün tələb olunan "
                    "adam sayı göstərilməyib."
                )
            )

        if people <= Decimal("0"):
            return EligibilityResult(
                eligible=False,
                code="INVALID_REQUIRED_PEOPLE",
                reason=(
                    "Operation-un tələb olunan "
                    "adam sayı 0-dan böyük olmalıdır."
                )
            )

        return None

    def _check_planned_mh(
        self,
        operation: SAPOperation
    ) -> Optional[EligibilityResult]:

        planned_mh = operation.planned_work_mh

        if planned_mh is None:
            return EligibilityResult(
                eligible=False,
                code="NO_PLANNED_MH",
                reason=(
                    "Operation üçün planlanan "
                    "adam-saat məlumatı yoxdur."
                )
            )

        if planned_mh <= Decimal("0"):
            return EligibilityResult(
                eligible=False,
                code="INVALID_PLANNED_MH",
                reason=(
                    "Planlanan adam-saat "
                    "0-dan böyük olmalıdır."
                )
            )

        return None

def evaluate_weekly_operations(
    weekly_plan,
    operations
):
    """
    Verilmiş operation siyahısını EligibilityEngine
    vasitəsilə yoxlayır.

    Nəticəni iki qrupa ayırır:
    - eligible
    - blocked
    """

    engine = EligibilityEngine()

    eligible = []
    blocked = []

    for operation in operations:

        result = engine.check(operation)

        item = {
            "operation": operation,
            "result": result,
        }

        if result.eligible:
            eligible.append(item)
        else:
            blocked.append(item)

    return {
        "weekly_plan": weekly_plan,
        "total": len(eligible) + len(blocked),
        "eligible": eligible,
        "blocked": blocked,
        "eligible_count": len(eligible),
        "blocked_count": len(blocked),
    }