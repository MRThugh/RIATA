"""
Backward-compatibility facade for ResponseGenerator in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Delegates to app.interaction.responses.ResponseEngine.
"""

from typing import Optional

from app.engine.intent import Intent
from app.executor.result import ExecutionResult
from app.interaction.responses import ResponseEngine, get_response_engine


class ResponseGenerator:
    """Facade delegating to ResponseEngine."""

    def __init__(self) -> None:
        self.engine = get_response_engine()

    def generate(self, result: ExecutionResult, intent: Intent) -> str:
        return self.engine.generate(result, intent)


_GLOBAL_RESPONSE_GEN: Optional[ResponseGenerator] = None


def get_response_generator() -> ResponseGenerator:
    """Retrieve global ResponseGenerator instance."""
    global _GLOBAL_RESPONSE_GEN
    if _GLOBAL_RESPONSE_GEN is None:
        _GLOBAL_RESPONSE_GEN = ResponseGenerator()
    return _GLOBAL_RESPONSE_GEN
