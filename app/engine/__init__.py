"""Engine package for R.I.A.T.A."""

from app.engine.entity_extractor import EntityExtractor, get_entity_extractor
from app.engine.intent import Intent
from app.engine.matcher import (
    BaseIntentParser,
    RuleBasedIntentParser,
    get_intent_parser,
)
from app.engine.normalizer import Normalizer, get_normalizer


def __getattr__(name: str):
    if name in ("IntentRouter", "ProcessOutput", "get_intent_router"):
        from app.engine.router import IntentRouter, ProcessOutput, get_intent_router
        globals().update({
            "IntentRouter": IntentRouter,
            "ProcessOutput": ProcessOutput,
            "get_intent_router": get_intent_router,
        })
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Intent",
    "Normalizer",
    "get_normalizer",
    "EntityExtractor",
    "get_entity_extractor",
    "BaseIntentParser",
    "RuleBasedIntentParser",
    "get_intent_parser",
    "IntentRouter",
    "ProcessOutput",
    "get_intent_router",
]
