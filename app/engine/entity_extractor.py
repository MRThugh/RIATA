"""
Entity extraction module for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

import re
from typing import Any, Optional

from app.core.constants import (
    INTENT_OPEN_APPLICATION,
    INTENT_OPEN_FILE,
    INTENT_OPEN_FOLDER,
    INTENT_PLAY_MUSIC,
    LANG_ENGLISH,
    LANG_PERSIAN,
)
from app.registry.applications import get_application_registry

# Standard XDG folder mappings (both Persian and English)
FOLDER_CANONICAL_MAP: dict[str, str] = {
    # Persian
    "دانلود": "Downloads",
    "دانلودها": "Downloads",
    "دانلود": "Downloads",
    "اسناد": "Documents",
    "داکیومنت": "Documents",
    "داکیومنتس": "Documents",
    "مدارک": "Documents",
    "تصاویر": "Pictures",
    "تصویر": "Pictures",
    "عکس": "Pictures",
    "عکسها": "Pictures",
    "عکس ها": "Pictures",
    "پیکچرز": "Pictures",
    "موزیک": "Music",
    "اهنگ": "Music",
    "اهنگها": "Music",
    "موسیقی": "Music",
    "موزیک ها": "Music",
    "ویدیو": "Videos",
    "ویدیوها": "Videos",
    "ویدیو ها": "Videos",
    "فیلم": "Videos",
    "فیلمها": "Videos",
    "فیلم ها": "Videos",
    "دسکتاپ": "Desktop",
    "میزکار": "Desktop",
    "میز کار": "Desktop",
    "خانه": "Home",
    "پوشه خانگی": "Home",
    "اصلی": "Home",
    # English
    "downloads": "Downloads",
    "download": "Downloads",
    "documents": "Documents",
    "document": "Documents",
    "docs": "Documents",
    "pictures": "Pictures",
    "picture": "Pictures",
    "photos": "Pictures",
    "images": "Pictures",
    "music": "Music",
    "songs": "Music",
    "audio": "Music",
    "videos": "Videos",
    "video": "Videos",
    "movies": "Videos",
    "desktop": "Desktop",
    "home": "Home",
}


class EntityExtractor:
    """Extracts and normalizes domain entities from user input."""

    def __init__(self) -> None:
        self.registry = get_application_registry()

    def extract(
        self, intent_name: str, normalized_text: str, language: str, raw_text: str = ""
    ) -> dict[str, Any]:
        """Extract entities relevant to the identified intent."""
        entities: dict[str, Any] = {}

        if intent_name == INTENT_OPEN_APPLICATION:
            app_entity = self._extract_application(normalized_text, language, raw_text)
            if app_entity:
                entities["application"] = app_entity

        elif intent_name == INTENT_OPEN_FOLDER:
            folder_entity = self._extract_folder(normalized_text, language)
            if folder_entity:
                entities["folder"] = folder_entity

        elif intent_name == INTENT_PLAY_MUSIC:
            song_entity = self._extract_song(normalized_text, language, raw_text)
            if song_entity:
                entities["song"] = song_entity

        elif intent_name == INTENT_OPEN_FILE:
            file_entity = self._extract_file(normalized_text, language)
            if file_entity:
                entities["file"] = file_entity

        return entities

    def _extract_application(
        self, text: str, language: str, raw_text: str
    ) -> Optional[str]:
        """Extract target application name."""
        cleaned = text.strip()

        # Check raw text for exact casing (e.g. "Firefox", "VS Code")
        # In Persian: "فایرفاکس رو باز کن" or "Firefox رو باز کن"
        if language == LANG_PERSIAN:
            # Match patterns like "<app> رو باز کن", "<app> را باز کن", "<app> باز کن", "برنامه <app> رو باز کن"
            patterns = [
                r"^(?:برنامه\s+)?(.+?)\s+(?:رو|را|رو\s+هم|را\s+هم)\s+(?:باز\s*کن|اجرا\s*کن|استارت\s*بزن|استارت\s*کن)$",
                r"^(?:برنامه\s+)?(.+?)\s+(?:باز\s*کن|اجرا\s*کن|استارت\s*بزن)$",
                r"^(?:باز\s*کن|اجرا\s*کن)\s+(?:برنامه\s+)?(.+?)$",
            ]
            for pat in patterns:
                m = re.match(pat, cleaned)
                if m:
                    extracted = m.group(1).strip()
                    # Strip residual markers
                    extracted = re.sub(r"^(?:برنامه|اپلیکیشن)\s+", "", extracted).strip()
                    extracted = re.sub(r"\s+(?:رو|را)$", "", extracted).strip()
                    if extracted:
                        return self._resolve_app_entity(extracted, raw_text)

        elif language == LANG_ENGLISH:
            # Match "open <app>", "launch <app>", "start <app>", "run <app>"
            patterns = [
                r"^(?:open|launch|start|run)\s+(?:app\s+|application\s+)?(.+?)$",
                r"^(?:open|launch|start|run)\s+(.+?)\s+(?:app|application)$",
            ]
            for pat in patterns:
                m = re.match(pat, cleaned)
                if m:
                    extracted = m.group(1).strip()
                    if extracted:
                        return self._resolve_app_entity(extracted, raw_text)

        # Fallback: check if any registered application name or alias is contained in the text
        for alias, app_id in self.registry._alias_map.items():
            if re.search(rf"\b{re.escape(alias)}\b", cleaned, flags=re.IGNORECASE):
                return app_id

        return None

    def _resolve_app_entity(self, extracted: str, raw_text: str) -> str:
        """Resolve extracted string against application registry or preserved casing."""
        app_entry = self.registry.find(extracted)
        if app_entry:
            return app_entry.id

        # If extracted text occurs in raw_text with original casing, extract original
        m = re.search(re.escape(extracted), raw_text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()

        return extracted

    def _extract_folder(self, text: str, language: str) -> Optional[str]:
        """Extract canonical folder name from text."""
        cleaned = text.strip()

        # Check known canonical folders first
        for key, canonical in FOLDER_CANONICAL_MAP.items():
            # Check standalone word or preceded by "پوشه" / "folder"
            pat = rf"(?:^|\s)(?:پوشه\s+|فولدر\s+|folder\s+)?{re.escape(key)}(?:\s|$)"
            if re.search(pat, cleaned, flags=re.IGNORECASE):
                return canonical

        # Generic pattern match: "پوشه <folder> رو باز کن" or "open <folder> folder"
        if language == LANG_PERSIAN:
            m = re.match(r"^(?:پوشه|فولدر)\s+(.+?)(?:\s+رو)?(?:\s+باز\s*کن|\s+نشون\s*بده)?$", cleaned)
            if m:
                target = m.group(1).strip()
                return FOLDER_CANONICAL_MAP.get(target, target.capitalize())
        else:
            m = re.match(r"^(?:open|show|explore)\s+(?:folder\s+)?(.+?)(?:\s+folder)?$", cleaned)
            if m:
                target = m.group(1).strip()
                return FOLDER_CANONICAL_MAP.get(target, target.capitalize())

        return None

    def _extract_song(
        self, text: str, language: str, raw_text: str
    ) -> Optional[str]:
        """Extract song title or null if user just requested generic playback."""
        cleaned = text.strip()

        # Persian: "آهنگ Another Love رو پخش کن" or "موزیک Another Love پخش کن"
        if language == LANG_PERSIAN:
            patterns = [
                r"^(?:اهنگ|موزیک|موسیقی)\s+(.+?)\s+(?:رو\s+)?(?:پخش\s*کن|پلی\s*کن|بذار)$",
                r"^پخش\s+(?:اهنگ|موزیک)\s+(.+)$",
            ]
            for pat in patterns:
                m = re.match(pat, cleaned)
                if m:
                    extracted = m.group(1).strip()
                    # Exclude generic words like "یه" or "یک"
                    if extracted in ("یه", "یک", "رو", "را"):
                        return None
                    return self._preserve_song_case(extracted, raw_text)

        elif language == LANG_ENGLISH:
            # English: "play Another Love", "play song Another Love"
            patterns = [
                r"^play\s+(?:song\s+|track\s+)?(.+)$",
            ]
            for pat in patterns:
                m = re.match(pat, cleaned)
                if m:
                    extracted = m.group(1).strip()
                    if extracted in ("music", "a song", "song", "some music"):
                        return None
                    return self._preserve_song_case(extracted, raw_text)

        return None

    def _preserve_song_case(self, extracted: str, raw_text: str) -> str:
        """Preserve original capitalization of the song title (e.g. Another Love)."""
        m = re.search(re.escape(extracted), raw_text, flags=re.IGNORECASE)
        if m:
            return m.group(0).strip()
        return extracted.title()

    def _extract_file(self, text: str, language: str) -> Optional[str]:
        """Extract target file path or name."""
        cleaned = text.strip()
        if language == LANG_PERSIAN:
            m = re.match(r"^فایل\s+(.+?)(?:\s+رو)?\s+(?:باز\s*کن|اجرا\s*کن)$", cleaned)
            if m:
                return m.group(1).strip()
        else:
            m = re.match(r"^open\s+file\s+(.+)$", cleaned)
            if m:
                return m.group(1).strip()
        return None


_GLOBAL_EXTRACTOR: Optional[EntityExtractor] = None


def get_entity_extractor() -> EntityExtractor:
    """Retrieve global EntityExtractor instance."""
    global _GLOBAL_EXTRACTOR
    if _GLOBAL_EXTRACTOR is None:
        _GLOBAL_EXTRACTOR = EntityExtractor()
    return _GLOBAL_EXTRACTOR
