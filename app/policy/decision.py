"""
Policy decisions for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass
from typing import Final, Optional

DECISION_ALLOW: Final[str] = "ALLOW"
DECISION_CONFIRM: Final[str] = "CONFIRM"
DECISION_DENY: Final[str] = "DENY"


@dataclass
class PolicyEvaluation:
    """Represents a security & risk evaluation decision for an Intent."""

    decision: str  # ALLOW, CONFIRM, or DENY
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    reason: str = ""
    action_label: str = ""
    confirmation_key: str = "confirm_action"

    @property
    def is_allowed(self) -> bool:
        return self.decision == DECISION_ALLOW

    @property
    def requires_confirmation(self) -> bool:
        return self.decision == DECISION_CONFIRM

    @property
    def is_denied(self) -> bool:
        return self.decision == DECISION_DENY
