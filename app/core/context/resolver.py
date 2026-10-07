"""
Deterministic Entity and Reference Resolver for R.I.A.T.A v0.2.0
Author: Ali Kamrani (MRThugh)

Resolves conversational pronouns, deictic references, and locative particles
(e.g. Persian 'ببندش', 'داخلش', 'همونو' / English 'close it', 'in it', 'that')
to prior active context entities, with strict ambiguity detection.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.context.models import SessionContext
from app.core.logger import get_logger

logger = get_logger("riata.context.resolver")


@dataclass
class ResolutionResult:
    """Result of attempting contextual entity resolution."""

    resolved: bool = False
    entities: dict[str, Any] = field(default_factory=dict)
    is_ambiguous: bool = False
    candidates: list[str] = field(default_factory=list)
    clarification_prompt: str = ""
    target_intent: Optional[str] = None


class ContextualEntityResolver:
    """
    Deterministic resolution of pronouns, relative clauses, and ambiguous targets.
    """

    # Persian contextual patterns
    FA_PRONOUN_SUFFIX = re.compile(r"(ببندش|بازش\s*کن|حذفش\s*کن|پاکش\s*کن|اجراش\s*کن)$")
    FA_LOCATIVE_IN = re.compile(r"^(داخلش|توش|در\s*آن|در\s*اون)\b")
    FA_DEMONSTRATIVE_SAME = re.compile(r"\b(همونو|همون|همین|قبلی)\b")

    # English contextual patterns
    EN_PRONOUN_IT = re.compile(r"\b(it|that|the\s+same|previous\s+one)\b", re.IGNORECASE)
    EN_LOCATIVE_IN = re.compile(r"\b(in\s+it|inside\s+it|in\s+that\s+folder|in\s+there)\b", re.IGNORECASE)

    def resolve(
        self,
        raw_text: str,
        parsed_intent_name: str,
        extracted_entities: dict[str, Any],
        context: SessionContext,
        language: str = "fa",
    ) -> ResolutionResult:
        """
        Resolve entities from explicit command tokens or contextual session memory.

        Resolution hierarchy:
        1. Explicit entity in current command
        2. Strongly matching contextual entity (pronoun/reference)
        3. Ambiguity check: if multiple candidate entities exist, request clarification!
        4. Compatible previous entity fallback
        """
        entities = dict(extracted_entities)
        lowered = raw_text.strip().lower()

        # 1. Check for explicit application state declaration
        # Example: "Chrome و Firefox باز هستند" / "Chrome and Firefox are open"
        open_state_detected = self._detect_open_state_declaration(lowered, language)
        if open_state_detected:
            # Update context's open_applications list with declared candidates
            context.open_applications = open_state_detected
            logger.info("Recorded active application candidates: %s", open_state_detected)

        # 2. Handle CLOSE_APPLICATION contextual resolution
        if parsed_intent_name == "CLOSE_APPLICATION":
            app_entity = entities.get("application")

            # Check if reference is explicit (e.g. "Chrome را ببند") or pronoun/relative ("ببندش", "close it", "ببند")
            is_explicit_app = bool(
                app_entity and str(app_entity).strip() not in ("ش", "it", "that", "این", "اون", "همونو", "همین")
            )

            if not is_explicit_app:
                # Ambiguity Check: Do we have multiple active candidates?
                active_candidates = [
                    a for a in context.open_applications if a
                ]
                if len(active_candidates) >= 2:
                    # Ambiguity! Do NOT guess. Require user clarification.
                    candidate_str = " یا ".join(active_candidates) if language == "fa" else " or ".join(active_candidates)
                    prompt = (
                        f"کدوم برنامه رو ببندم؟ {candidate_str}؟"
                        if language == "fa"
                        else f"Which application should I close? {candidate_str}?"
                    )
                    logger.info("Ambiguity detected closing application among candidates: %s", active_candidates)
                    return ResolutionResult(
                        resolved=False,
                        entities={},
                        is_ambiguous=True,
                        candidates=active_candidates,
                        clarification_prompt=prompt,
                        target_intent="CLOSE_APPLICATION",
                    )

                # Exactly one candidate available in context
                target_app = None
                if active_candidates:
                    target_app = active_candidates[0]
                elif context.active_application:
                    target_app = context.active_application

                if target_app:
                    entities["application"] = target_app
                    logger.info("Contextually resolved application '%s' for CLOSE_APPLICATION", target_app)
                    return ResolutionResult(
                        resolved=True,
                        entities=entities,
                        target_intent="CLOSE_APPLICATION",
                    )
            else:
                # Explicit application specified by user — explicit entity MUST win!
                return ResolutionResult(
                    resolved=True,
                    entities=entities,
                    target_intent="CLOSE_APPLICATION",
                )

        # 3. Handle CREATE_FILE contextual locative resolution ("داخلش فایل test.txt رو بساز")
        if parsed_intent_name == "CREATE_FILE":
            folder_entity = entities.get("folder")
            has_locative = (
                bool(self.FA_LOCATIVE_IN.search(lowered))
                or "داخلش" in lowered
                or "توش" in lowered
                or bool(self.EN_LOCATIVE_IN.search(lowered))
            )
            if not folder_entity and has_locative and context.active_directory:
                entities["folder"] = context.active_directory
                logger.info("Contextually resolved active directory '%s' for CREATE_FILE", context.active_directory)
                return ResolutionResult(
                    resolved=True,
                    entities=entities,
                    target_intent="CREATE_FILE",
                )

        # 4. Handle DELETE_FILE contextual resolution ("حذفش کن", "delete it")
        if parsed_intent_name == "DELETE_FILE":
            file_entity = entities.get("file")
            is_explicit_file = bool(
                file_entity and str(file_entity).strip() not in ("ش", "it", "that", "این", "اون", "همونو")
            )
            if not is_explicit_file and context.active_file:
                entities["file"] = context.active_file
                logger.info("Contextually resolved active file '%s' for DELETE_FILE", context.active_file)
                return ResolutionResult(
                    resolved=True,
                    entities=entities,
                    target_intent="DELETE_FILE",
                )

        # 5. Handle OPEN_APPLICATION / OPEN_FOLDER contextual references ("بازش کن", "همونو باز کن")
        if parsed_intent_name == "OPEN_APPLICATION":
            app_entity = entities.get("application")
            is_explicit_app = bool(
                app_entity and str(app_entity).strip() not in ("ش", "it", "همونو", "همین")
            )
            if not is_explicit_app and context.active_application:
                entities["application"] = context.active_application
                logger.info("Contextually resolved active application '%s'", context.active_application)
                return ResolutionResult(
                    resolved=True,
                    entities=entities,
                    target_intent="OPEN_APPLICATION",
                )

        return ResolutionResult(
            resolved=bool(entities),
            entities=entities,
            target_intent=parsed_intent_name,
        )

    def _detect_open_state_declaration(self, lowered: str, language: str) -> list[str]:
        """
        Detect user declaring running applications:
        e.g. "Chrome و Firefox باز هستند" or "Chrome and Firefox are open"
        """
        candidates: list[str] = []
        if language == "fa":
            # Match e.g. "chrome و firefox باز هستند"
            m = re.search(r"(.+?)\s+(?:باز\s*هستند|در\s*حال\s*اجرا\s*هستند|بازن)", lowered)
            if m:
                segment = m.group(1).replace("برنامه های", "").replace("برنامه‌های", "").replace("برنامه", "")
                parts = re.split(r"\s+و\s+|\s*,\s*", segment)
                for p in parts:
                    clean = p.strip()
                    if clean and len(clean) > 1:
                        candidates.append(clean.capitalize())
        else:
            m = re.search(r"(.+?)\s+(?:are\s+open|are\s+running)", lowered, re.IGNORECASE)
            if m:
                segment = m.group(1).replace("the apps", "").replace("apps", "")
                parts = re.split(r"\s+and\s+|\s*,\s*", segment, flags=re.IGNORECASE)
                for p in parts:
                    clean = p.strip()
                    if clean and len(clean) > 1:
                        candidates.append(clean.capitalize())

        return candidates
