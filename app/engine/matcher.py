"""
Rule-based Intent Parser and Matcher for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Architecture:
Language-independent Intent Parser driven by Language Packs.
Outputs language-independent Intent structures.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.constants import (
    CONFIDENCE_EXACT,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    DANGEROUS_COMMANDS,
    INTENT_CLARIFY,
    INTENT_CLOSE_APPLICATION,
    INTENT_CREATE_FILE,
    INTENT_DELETE_FILE,
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_FOLDER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_OPEN_URL,
    INTENT_PLAY_MUSIC,
    INTENT_RESET_CONTEXT,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
    INTENT_UNKNOWN,
    LANG_AUTO,
)
from app.core.logger import get_logger
from app.engine.entity_extractor import FOLDER_CANONICAL_MAP, get_entity_extractor
from app.engine.intent import Intent
from app.engine.normalizer import get_normalizer
from app.languages.detector import detect_language
from app.languages.registry import LanguagePack, get_language_registry
from app.registry.applications import get_application_registry

logger = get_logger("riata.matcher")


class BaseIntentParser(ABC):
    """Abstract interface for intent parsing."""

    @abstractmethod
    def parse(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        """Parse natural language into a structured Intent."""
        pass


class RuleBasedIntentParser(BaseIntentParser):
    """
    Deterministic, extensible, rule-based Intent Engine for R.I.A.T.A v0.1.1.

    Separates language understanding from action execution.
    Outputs language-independent Intent structures.
    """

    def __init__(self) -> None:
        self.registry = get_language_registry()
        self.normalizer = get_normalizer()
        self.extractor = get_entity_extractor()
        self.app_registry = get_application_registry()

    def parse(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        """Parse user input into structured Intent."""
        raw_text = text.strip() if text else ""
        if not raw_text:
            return Intent.unknown(raw_text)

        # 1. Safety check for dangerous or malicious shell commands
        if self._is_dangerous(raw_text):
            logger.warning("Dangerous command detected and blocked: %s", raw_text)
            return Intent(
                name=INTENT_UNKNOWN,
                confidence=0.0,
                raw_text=raw_text,
                normalized_text=raw_text,
                language="en",
                is_dangerous=True,
            )

        # 2. Contextual follow-up check (e.g. selection or confirmation)
        if context and context.get("awaiting_selection"):
            handled = self._handle_context_selection(raw_text, context)
            if handled:
                return handled

        # 3. Language detection (queries registered Language Packs)
        lang = detect_language(raw_text, preferred=LANG_AUTO)
        logger.info("Language detected: %s", lang)
        pack: LanguagePack = self.registry.get(lang)

        # 4. Normalization
        normalized = self.normalizer.normalize(raw_text, language=lang)
        # Strip conversational fillers/polite particles for matching
        clean_command = self.normalizer.strip_conversational_particles(normalized, language=lang)

        # 5. Check if query is too vague (e.g. "اون رو باز کن" / "open that") using pack definition
        if pack.is_vague(clean_command):
            logger.info("Vague command received, asking for clarification: %s", raw_text)
            clarify_prompt = pack.get_response(
                "clarify_application",
                default="Could you please specify which application to open?",
            )
            return Intent(
                name=INTENT_CLARIFY,
                confidence=CONFIDENCE_MEDIUM,
                entities={},
                raw_text=raw_text,
                normalized_text=clean_command,
                language=lang,
                is_clarification_needed=True,
                clarification_prompt=clarify_prompt,
            )

        # 6. Intent matching pipeline
        intent = self._match_intents(raw_text, clean_command, lang)

        logger.info("Intent: %s (confidence: %.2f)", intent.name, intent.confidence)
        if intent.entities:
            for k, v in intent.entities.items():
                logger.info("Entity: %s = %s", k, v)

        return intent

    def _is_dangerous(self, text: str) -> bool:
        """Detect dangerous shell commands strictly using tokens and boundaries."""
        lowered = text.lower().strip()
        tokens = set(re.split(r"[\s+|;&`$()<>\\]+", lowered))

        for dangerous in DANGEROUS_COMMANDS:
            if not dangerous.isalnum() and dangerous in lowered:
                return True
            if dangerous in tokens:
                return True

        if ">" in lowered or "<" in lowered or "`" in lowered or "$(" in lowered:
            return True

        if re.search(r"\brm\s+-[a-zA-Z]*r", lowered) or re.search(r"\brm\s+", lowered):
            return True
        if re.search(r"\bsudo\s+", lowered) or re.search(r"\bsu\s+", lowered):
            return True
        if re.search(r"\bmkfs\b", lowered) or re.search(r"\bshutdown\b", lowered) or re.search(r"\breboot\b", lowered):
            return True
        if ":(){ :|:& };:" in lowered:
            return True

        return False

    def _handle_context_selection(
        self, text: str, context: dict[str, Any]
    ) -> Optional[Intent]:
        """Handle selection from a previous disambiguation prompt."""
        candidates = context.get("candidates", [])
        if not candidates:
            return None

        cleaned = text.strip().lower()
        num: Optional[int] = None

        if cleaned.isdigit():
            num = int(cleaned)
        else:
            # Check ordinals from active language pack or all packs
            lang = context.get("language", "en")
            pack = self.registry.get(lang)
            ordinals = dict(pack.get_ordinals())
            for c in self.registry.get_supported_codes():
                ordinals.update(self.registry.get(c).get_ordinals())

            if cleaned in ordinals:
                num = ordinals[cleaned]

        if num is not None and 1 <= num <= len(candidates):
            selected = candidates[num - 1]
            target_intent = context.get("intent", INTENT_PLAY_MUSIC)
            entities = dict(context.get("entities", {}))
            if target_intent == INTENT_PLAY_MUSIC:
                entities["song"] = selected
                entities["selected_path"] = selected
            elif target_intent == INTENT_OPEN_APPLICATION:
                entities["application"] = selected

            return Intent(
                name=target_intent,
                confidence=CONFIDENCE_EXACT,
                entities=entities,
                raw_text=text,
                normalized_text=cleaned,
                language=context.get("language", "en"),
            )

        # Check if text matches candidate name directly
        for cand in candidates:
            cand_str = str(cand).lower()
            if cleaned in cand_str:
                target_intent = context.get("intent", INTENT_PLAY_MUSIC)
                entities = dict(context.get("entities", {}))
                if target_intent == INTENT_PLAY_MUSIC:
                    entities["song"] = cand
                    entities["selected_path"] = cand
                return Intent(
                    name=target_intent,
                    confidence=CONFIDENCE_EXACT,
                    entities=entities,
                    raw_text=text,
                    normalized_text=cleaned,
                    language=context.get("language", "en"),
                )

        return None

    def _match_intents(self, raw_text: str, text: str, lang: str) -> Intent:
        """Match input against language-pack intent rules."""
        pack = self.registry.get(lang)
        intents_config = pack.intents

        # Fixed order of resolution
        fixed_order = [
            INTENT_RESET_CONTEXT,
            INTENT_EXIT_APPLICATION,
            INTENT_SHOW_SYSTEM_INFO,
            INTENT_TAKE_SCREENSHOT,
            INTENT_OPEN_TERMINAL,
            INTENT_OPEN_FILE_MANAGER,
            INTENT_OPEN_SETTINGS,
            INTENT_PLAY_MUSIC,
            INTENT_CLOSE_APPLICATION,
            INTENT_DELETE_FILE,
            INTENT_CREATE_FILE,
            INTENT_OPEN_FILE,
            INTENT_OPEN_FOLDER,
            INTENT_OPEN_URL,
            INTENT_OPEN_APPLICATION,
        ]

        for intent_name in fixed_order:
            intent_data = intents_config.get(intent_name, {})
            patterns = intent_data.get("patterns", [])

            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    # Match found! Extract entities
                    entities = self.extractor.extract(
                        intent_name, text, lang, raw_text=raw_text
                    )

                    confidence = CONFIDENCE_HIGH
                    if intent_name in (
                        INTENT_OPEN_TERMINAL,
                        INTENT_OPEN_FILE_MANAGER,
                        INTENT_OPEN_SETTINGS,
                        INTENT_SHOW_SYSTEM_INFO,
                        INTENT_TAKE_SCREENSHOT,
                        INTENT_EXIT_APPLICATION,
                    ):
                        confidence = CONFIDENCE_EXACT
                    elif intent_name == INTENT_OPEN_APPLICATION:
                        app_ent = entities.get("application")
                        if app_ent and app_ent.lower() in FOLDER_CANONICAL_MAP:
                            intent_name = INTENT_OPEN_FOLDER
                            entities = {"folder": FOLDER_CANONICAL_MAP[app_ent.lower()]}
                            confidence = CONFIDENCE_EXACT
                        elif app_ent:
                            entry = self.app_registry.find(app_ent)
                            confidence = CONFIDENCE_EXACT if entry else CONFIDENCE_HIGH
                        else:
                            confidence = CONFIDENCE_MEDIUM
                    elif intent_name == INTENT_OPEN_FOLDER:
                        confidence = CONFIDENCE_EXACT if entities.get("folder") else CONFIDENCE_MEDIUM
                    elif intent_name == INTENT_PLAY_MUSIC:
                        confidence = CONFIDENCE_HIGH

                    return Intent(
                        name=intent_name,
                        confidence=confidence,
                        entities=entities,
                        raw_text=raw_text,
                        normalized_text=text,
                        language=lang,
                    )

        # Fallback check: Did user mention an application directly?
        app_entry = self.app_registry.find(text)
        if app_entry:
            return Intent(
                name=INTENT_OPEN_APPLICATION,
                confidence=CONFIDENCE_HIGH,
                entities={"application": app_entry.id},
                raw_text=raw_text,
                normalized_text=text,
                language=lang,
            )

        # Fallback check: Did user mention a canonical folder directly?
        folder_ent = self.extractor._extract_folder(text, pack)
        if folder_ent:
            return Intent(
                name=INTENT_OPEN_FOLDER,
                confidence=CONFIDENCE_HIGH,
                entities={"folder": folder_ent},
                raw_text=raw_text,
                normalized_text=text,
                language=lang,
            )

        return Intent.unknown(raw_text, language=lang)


_GLOBAL_MATCHER: Optional[RuleBasedIntentParser] = None


def get_intent_parser() -> BaseIntentParser:
    """Retrieve global IntentParser instance."""
    global _GLOBAL_MATCHER
    if _GLOBAL_MATCHER is None:
        _GLOBAL_MATCHER = RuleBasedIntentParser()
    return _GLOBAL_MATCHER
