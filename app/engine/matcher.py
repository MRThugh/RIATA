"""
Rule-based Intent Parser and Matcher for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Optional

from app.core.constants import (
    CONFIDENCE_EXACT,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    DANGEROUS_COMMANDS,
    INTENT_CLARIFY,
    INTENT_EXIT_APPLICATION,
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FILE_MANAGER,
    INTENT_OPEN_FOLDER,
    INTENT_OPEN_SETTINGS,
    INTENT_OPEN_TERMINAL,
    INTENT_PLAY_MUSIC,
    INTENT_SHOW_SYSTEM_INFO,
    INTENT_TAKE_SCREENSHOT,
    INTENT_UNKNOWN,
    LANG_AUTO,
    LANG_ENGLISH,
    LANG_PERSIAN,
)
from app.core.logger import get_logger
from app.engine.entity_extractor import FOLDER_CANONICAL_MAP, get_entity_extractor
from app.engine.intent import Intent
from app.engine.normalizer import get_normalizer
from app.languages.detector import detect_language
from app.languages.loader import get_language_loader
from app.registry.applications import get_application_registry

logger = get_logger("riata.matcher")


class BaseIntentParser(ABC):
    """Abstract interface for intent parsing (ensures future AI compatibility)."""

    @abstractmethod
    def parse(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        """Parse natural language into a structured Intent."""
        pass


class RuleBasedIntentParser(BaseIntentParser):
    """
    Deterministic, extensible, rule-based Intent Engine for R.I.A.T.A v0.1.0.

    Separates language understanding from action execution.
    Outputs language-independent Intent structures.
    """

    def __init__(self) -> None:
        self.loader = get_language_loader()
        self.normalizer = get_normalizer()
        self.extractor = get_entity_extractor()
        self.registry = get_application_registry()

    def parse(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        """Parse user input into structured Intent."""
        raw_text = text.strip() if text else ""
        if not raw_text:
            return Intent.unknown(raw_text)

        # 1. Safety check for dangerous or malicious commands
        if self._is_dangerous(raw_text):
            logger.warning("Dangerous command detected and blocked: %s", raw_text)
            return Intent(
                name=INTENT_UNKNOWN,
                confidence=0.0,
                raw_text=raw_text,
                normalized_text=raw_text,
                language=LANG_ENGLISH,
                is_dangerous=True,
            )

        # 2. Contextual follow-up check (e.g. user selecting option 1, 2 or answering a question)
        if context and context.get("awaiting_selection"):
            handled = self._handle_context_selection(raw_text, context)
            if handled:
                return handled

        # 3. Language detection
        lang = detect_language(raw_text, preferred=LANG_AUTO)
        logger.info("Language detected: %s", lang)

        # 4. Normalization
        normalized = self.normalizer.normalize(raw_text, language=lang)
        # Strip conversational fillers/polite particles for matching
        clean_command = self.normalizer.strip_conversational_particles(normalized, language=lang)

        # 5. Check if query is too vague (e.g. "اون رو باز کن" / "open that")
        if self._is_vague_open(clean_command, lang):
            logger.info("Vague command received, asking for clarification: %s", raw_text)
            clarify_prompt = (
                "من دقیق متوجه نشدم. میتونی بگی کدوم برنامه رو باز کنم؟"
                if lang == LANG_PERSIAN
                else "I didn't quite catch that. Could you specify which application to open?"
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

        if ">" in lowered or "<" in lowered:
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

    def _is_vague_open(self, text: str, lang: str) -> bool:
        """Check for ambiguous open requests lacking an entity."""
        if lang == LANG_PERSIAN:
            vague_patterns = [
                r"^اون\s+رو\s+باز\s*کن$",
                r"^اینو\s+باز\s*کن$",
                r"^اونه\s+رو\s+باز\s*کن$",
                r"^باز\s*کن$",
                r"^اجرا\s*کن$",
                r"^برنامه\s+رو\s+باز\s*کن$",
            ]
        else:
            vague_patterns = [
                r"^open\s+that$",
                r"^open\s+it$",
                r"^open\s+this$",
                r"^open\s+the\s+app$",
                r"^launch\s+it$",
                r"^run\s+it$",
                r"^open$",
            ]
        return any(re.match(pat, text, re.IGNORECASE) for pat in vague_patterns)

    def _handle_context_selection(
        self, text: str, context: dict[str, Any]
    ) -> Optional[Intent]:
        """Handle selection from a previous disambiguation prompt."""
        candidates = context.get("candidates", [])
        if not candidates:
            return None

        # Check numeric selection ("1", "2", "اول", "دومی")
        cleaned = text.strip()
        num: Optional[int] = None

        if cleaned.isdigit():
            num = int(cleaned)
        elif cleaned in ("اول", "اولی", "اولین", "first", "1st"):
            num = 1
        elif cleaned in ("دوم", "دومی", "دومین", "second", "2nd"):
            num = 2
        elif cleaned in ("سوم", "سومی", "سومین", "third", "3rd"):
            num = 3

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
                language=context.get("language", LANG_ENGLISH),
            )

        # Check if text matches candidate name directly
        for cand in candidates:
            cand_str = str(cand).lower()
            if cleaned.lower() in cand_str:
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
                    language=context.get("language", LANG_ENGLISH),
                )

        return None

    def _match_intents(self, raw_text: str, text: str, lang: str) -> Intent:
        """Match input against language-pack intent rules."""
        pack = self.loader.get_pack(lang)
        intents_config = pack.intents

        # 1. Direct system utility intents (terminal, file manager, settings, system info, exit, screenshot)
        fixed_order = [
            INTENT_EXIT_APPLICATION,
            INTENT_SHOW_SYSTEM_INFO,
            INTENT_TAKE_SCREENSHOT,
            INTENT_OPEN_TERMINAL,
            INTENT_OPEN_FILE_MANAGER,
            INTENT_OPEN_SETTINGS,
            INTENT_PLAY_MUSIC,
            INTENT_OPEN_FOLDER,
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
                            # User said e.g. "Downloads رو باز کن" or "open Downloads"
                            intent_name = INTENT_OPEN_FOLDER
                            entities = {"folder": FOLDER_CANONICAL_MAP[app_ent.lower()]}
                            confidence = CONFIDENCE_EXACT
                        elif app_ent:
                            # Higher confidence if found in registry
                            entry = self.registry.find(app_ent)
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

        # Fallback check: Did user mention an application directly (e.g. "firefox", "فایرفاکس")?
        app_entry = self.registry.find(text)
        if app_entry:
            return Intent(
                name=INTENT_OPEN_APPLICATION,
                confidence=CONFIDENCE_HIGH,
                entities={"application": app_entry.id},
                raw_text=raw_text,
                normalized_text=text,
                language=lang,
            )

        # Fallback check: Did user mention a canonical folder directly (e.g. "Downloads", "دانلودها")?
        folder_ent = self.extractor._extract_folder(text, lang)
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
