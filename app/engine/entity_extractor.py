"""
Entity extraction module for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Architecture:
Language-agnostic entity extractor consuming declarative Language Packs.
Core does not contain language-specific if/elif branching.
"""

import re
from typing import Any, Optional

from app.core.constants import (
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FOLDER,
    INTENT_PLAY_MUSIC,
)
from app.languages.registry import LanguagePack, get_language_registry
from app.registry.applications import get_application_registry


class _CombinedFolderMap(dict):
    """Dynamic dict view combining canonical folder maps from all registered packs."""

    def __init__(self) -> None:
        super().__init__()
        self._refresh()

    def _refresh(self) -> None:
        try:
            reg = get_language_registry()
            for code in reg.get_supported_codes():
                pack = reg.get(code)
                self.update(pack.get_folder_map())
        except Exception:
            pass

    def __getitem__(self, key: str) -> str:
        self._refresh()
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        self._refresh()
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        self._refresh()
        return super().__contains__(key)

    def items(self):
        self._refresh()
        return super().items()


# Backward-compatible global folder mapping dynamically populated from language packs
FOLDER_CANONICAL_MAP = _CombinedFolderMap()


class EntityExtractor:
    """Extracts and normalizes domain entities from user input using Language Packs."""

    def __init__(self) -> None:
        self.app_registry = get_application_registry()
        self.lang_registry = get_language_registry()

    def extract(
        self, intent_name: str, normalized_text: str, language: str, raw_text: str = ""
    ) -> dict[str, Any]:
        """Extract entities relevant to the identified intent using the language pack."""
        pack = self.lang_registry.get(language)

        # 1. Custom rule hook if pack provides one
        if pack.rules:
            custom_entities = pack.rules.extract_entities(intent_name, normalized_text, raw_text)
            if custom_entities is not None:
                return custom_entities

        # 2. Declarative extraction
        entities: dict[str, Any] = {}

        if intent_name in (INTENT_OPEN_APPLICATION, "CLOSE_APPLICATION"):
            app_entity = self._extract_application(normalized_text, pack, raw_text)
            if app_entity:
                entities["application"] = app_entity

        elif intent_name in (INTENT_OPEN_FOLDER, "CREATE_FOLDER", "DELETE_FOLDER"):
            folder_entity = self._extract_folder(normalized_text, pack)
            if folder_entity:
                entities["folder"] = folder_entity

        elif intent_name == INTENT_PLAY_MUSIC:
            song_entity = self._extract_song(normalized_text, pack, raw_text)
            if song_entity:
                entities["song"] = song_entity

        elif intent_name in (INTENT_OPEN_FILE, "CREATE_FILE", "DELETE_FILE"):
            file_entity = self._extract_file(normalized_text, pack, raw_text=raw_text)
            if file_entity:
                entities["file"] = file_entity
            folder_entity = self._extract_folder(normalized_text, pack)
            if folder_entity:
                entities["folder"] = folder_entity

        elif intent_name == "OPEN_URL":
            entities["url"] = self._extract_url(normalized_text, raw_text)

        return entities

    def _extract_url(self, text: str, raw_text: str) -> str:
        """Extract web URL or domain."""
        cleaned = text.strip()
        m = re.search(r"(https?://\S+)", raw_text)
        if m:
            return m.group(1)
        for token in cleaned.split():
            if "." in token and not token.endswith(".") and "/" not in token:
                return token
        return cleaned

    def _extract_application(
        self, text: str, pack: LanguagePack, raw_text: str
    ) -> Optional[str]:
        """Extract target application name using pack declarative patterns."""
        cleaned = text.strip()

        patterns = pack.entities.get("application_patterns", [])
        prefixes = pack.entities.get("application_prefixes_to_strip", [])
        suffixes = pack.entities.get("application_suffixes_to_strip", [])

        for pat in patterns:
            m = re.match(pat, cleaned, flags=re.IGNORECASE)
            if m:
                # Extract named group 'app' or first group
                extracted = m.groupdict().get("app") if "app" in m.groupdict() else m.group(1)
                if extracted:
                    extracted = extracted.strip()
                    # Strip prefixes
                    for pref in prefixes:
                        extracted = re.sub(rf"^{re.escape(pref)}\s+", "", extracted, flags=re.IGNORECASE).strip()
                    # Strip suffixes
                    for suff in suffixes:
                        extracted = re.sub(rf"\s+{re.escape(suff)}$", "", extracted, flags=re.IGNORECASE).strip()

                    if extracted:
                        return self._resolve_app_entity(extracted, raw_text)

        # Fallback: check if any registered application name or alias is contained in the text
        for alias, app_id in self.app_registry._alias_map.items():
            if re.search(rf"\b{re.escape(alias)}\b", cleaned, flags=re.IGNORECASE):
                return app_id

        return None

    def _resolve_app_entity(self, extracted: str, raw_text: str) -> str:
        """Resolve extracted string against application registry or preserved casing."""
        app_entry = self.app_registry.find(extracted)
        if app_entry:
            return app_entry.id

        # If extracted text occurs in raw_text with original casing, extract original
        m = re.search(re.escape(extracted), raw_text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()

        return extracted

    def _extract_folder(self, text: str, pack: LanguagePack) -> Optional[str]:
        """Extract canonical folder name from text using pack definitions and combined map."""
        cleaned = text.strip()

        # Check combined folder map (allows e.g. "Downloads" mentioned in Persian commands)
        for key, canonical in FOLDER_CANONICAL_MAP.items():
            pat = rf"(?:^|\s)(?:پوشه\s+|فولدر\s+|folder\s+)?{re.escape(key)}(?:\s|$)"
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                return canonical

        # Generic pattern match from pack
        patterns = pack.entities.get("folder_patterns", [])
        for pat in patterns:
            m = re.match(pat, cleaned, flags=re.IGNORECASE)
            if m:
                target = m.groupdict().get("folder") if "folder" in m.groupdict() else m.group(1)
                if target:
                    target = target.strip()
                    return FOLDER_CANONICAL_MAP.get(target, target.capitalize())

        return None

    def _extract_song(
        self, text: str, pack: LanguagePack, raw_text: str
    ) -> Optional[str]:
        """Extract song title or null if user just requested generic playback."""
        cleaned = text.strip()
        patterns = pack.entities.get("song_patterns", [])
        ignore_words = pack.entities.get("song_ignore_words", [])

        for pat in patterns:
            m = re.match(pat, cleaned, flags=re.IGNORECASE)
            if m:
                extracted = m.groupdict().get("song") if "song" in m.groupdict() else m.group(1)
                if extracted:
                    extracted = extracted.strip()
                    if extracted in ignore_words or extracted.lower() in [w.lower() for w in ignore_words]:
                        return None
                    return self._preserve_song_case(extracted, raw_text)

        return None

    def _preserve_song_case(self, extracted: str, raw_text: str) -> str:
        """Preserve original capitalization of the song title (e.g. Another Love)."""
        m = re.search(re.escape(extracted), raw_text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
        return extracted.title()

    def _extract_file(self, text: str, pack: LanguagePack, raw_text: str = "") -> Optional[str]:
        """Extract target file path or name."""
        cleaned = text.strip()

        # Check raw_text first for filenames with extension (e.g. test.txt, report.pdf)
        if raw_text:
            m = re.search(r"\b([a-zA-Z0-9_\-.]+\.[a-zA-Z0-9]{1,5})\b", raw_text)
            if m:
                return m.group(1).strip()

        patterns = pack.entities.get("file_patterns", [])

        for pat in patterns:
            m = re.match(pat, cleaned, flags=re.IGNORECASE)
            if m:
                extracted = m.groupdict().get("file") if "file" in m.groupdict() else m.group(1)
                if extracted:
                    return extracted.strip()

        # Fallback for filenames with extension (e.g. test.txt, report.pdf)
        m = re.search(r"\b([a-zA-Z0-9_\-.]+\.[a-zA-Z0-9]{1,5})\b", cleaned)
        if m:
            return m.group(1).strip()

        if cleaned in ("حذفش کن", "پاکش کن", "delete it", "ببندش"):
            return "ش"

        return None


_GLOBAL_EXTRACTOR: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Retrieve global EntityExtractor instance."""
    global _GLOBAL_EXTRACTOR
    if _GLOBAL_EXTRACTOR is None:
        _GLOBAL_EXTRACTOR = EntityExtractor()
    return _GLOBAL_EXTRACTOR
