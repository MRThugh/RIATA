"""
Extensible Language Registry and Language Pack architecture for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Follows the design principle:
Language Pack -> Language Registry -> Language-Agnostic Core -> Intent -> Router -> Executor
The core consumes a Language Pack instead of containing language-specific logic.
"""

import importlib.util
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.logger import get_logger
from app.languages.rules import BaseLanguageRules

logger = get_logger("riata.languages.registry")


class InvalidLanguagePackError(Exception):
    """Raised when a language pack fails metadata or schema validation."""
    pass


@dataclass
class LanguagePack:
    """
    Complete language pack representation.
    Decouples language understanding, normalization, entity extraction,
    and localized responses from the core engine.
    """

    code: str
    name: str
    english_name: str
    direction: str = "ltr"  # 'rtl' or 'ltr'
    version: str = "0.1.1"
    native_name: str = ""
    script_pattern: Optional[str] = None
    responses: dict[str, Any] = field(default_factory=dict)
    intents: dict[str, Any] = field(default_factory=dict)
    normalization: dict[str, Any] = field(default_factory=dict)
    entities: dict[str, Any] = field(default_factory=dict)
    conversational: dict[str, Any] = field(default_factory=dict)
    rules: Optional[BaseLanguageRules] = None

    def __post_init__(self) -> None:
        if not self.native_name:
            self.native_name = self.name

    def get_response(self, key: str, default: str = "", **kwargs: Any) -> str:
        """Format a localized response string using keyword parameters safely."""
        template = self.responses.get(key, default)
        if not template:
            return default
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError) as err:
            logger.warning("Missing format key %s in response %s", err, key)
            return str(template)

    def get_folder_map(self) -> dict[str, str]:
        """Return localized folder name to canonical XDG folder mapping."""
        return self.entities.get("folders", {})

    def get_ordinals(self) -> dict[str, int]:
        """Return localized ordinal terms mapping (e.g. 'اول' -> 1, 'first' -> 1)."""
        return self.entities.get("ordinals", {})

    def is_confirmation(self, text: str) -> bool:
        """Check if user text signifies positive confirmation."""
        clean = text.strip().lower()
        confirm_words = self.conversational.get(
            "confirmations", ["yes", "y", "sure", "ok", "yep", "بله", "آره", "اره", "درسته", "تایید"]
        )
        return clean in [w.lower() for w in confirm_words]

    def is_cancellation(self, text: str) -> bool:
        """Check if user text signifies cancellation/denial."""
        clean = text.strip().lower()
        cancel_words = self.conversational.get(
            "cancellations", ["no", "n", "cancel", "stop", "abort", "نه", "خیر", "لغو", "کنسل", "بیخیال"]
        )
        return clean in [w.lower() for w in cancel_words]

    def is_vague(self, text: str) -> bool:
        """Check if user command matches known vague patterns for this language."""
        patterns = self.conversational.get("vague_patterns", [])
        for pat in patterns:
            if re.match(pat, text, re.IGNORECASE):
                return True
        return False


class LanguageRegistry:
    """
    Central registry for language packs.
    Discovers, validates, and manages language packs without hardcoding
    language-specific logic in the core engine.
    """

    def __init__(self, languages_dir: Optional[Path] = None) -> None:
        if languages_dir is None:
            candidates = [
                Path.cwd() / "languages",
                Path(__file__).resolve().parent.parent.parent / "languages",
            ]
            for candidate in candidates:
                if candidate.is_dir():
                    languages_dir = candidate
                    break
            if languages_dir is None:
                languages_dir = Path.cwd() / "languages"

        self.languages_dir = languages_dir
        self._packs: dict[str, LanguagePack] = {}
        self.discover()

    def discover(self, directory: Optional[Path] = None) -> None:
        """Scan directory and load all valid language packs."""
        search_dir = directory or self.languages_dir
        if not search_dir.exists():
            logger.warning("Languages directory does not exist: %s", search_dir)
            return

        for item in search_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                try:
                    pack = self.load_pack(item)
                    if pack:
                        self.register(pack)
                except InvalidLanguagePackError as e:
                    logger.warning("Invalid language pack in %s: %s", item, e)
                except Exception as e:
                    logger.error("Failed to load language pack from %s: %s", item, e)

    def load_pack(self, pack_dir: Path) -> LanguagePack:
        """
        Load a language pack from directory.
        Supports:
        - manifest.json or language.json
        - intents.json
        - normalization.json
        - entities.json
        - responses.json
        - conversational.json
        - rules.py
        """
        # 1. Metadata check: manifest.json takes priority, fall back to language.json
        manifest_file = pack_dir / "manifest.json"
        legacy_file = pack_dir / "language.json"

        meta_path = manifest_file if manifest_file.is_file() else (legacy_file if legacy_file.is_file() else None)
        if not meta_path:
            raise InvalidLanguagePackError(f"No manifest.json or language.json in {pack_dir}")

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            raise InvalidLanguagePackError(f"Could not read metadata from {meta_path}: {e}")

        # Validation of required fields
        code = meta.get("code") or meta.get("id") or pack_dir.name
        name = meta.get("name")
        if not name:
            raise InvalidLanguagePackError(f"Language pack in {pack_dir} missing 'name'")

        english_name = meta.get("english_name", name)
        native_name = meta.get("native_name", name)
        direction = meta.get("direction", "ltr")
        if direction not in ("ltr", "rtl"):
            raise InvalidLanguagePackError(f"Invalid direction '{direction}' in {pack_dir}")

        version = meta.get("version", "0.1.1")
        script_pattern = meta.get("script_pattern")

        # 2. Responses (from responses.json or manifest/language.json)
        responses: dict[str, Any] = dict(meta.get("responses", {}))
        resp_file = pack_dir / "responses.json"
        if resp_file.is_file():
            try:
                with open(resp_file, "r", encoding="utf-8") as f:
                    resp_data = json.load(f)
                    if isinstance(resp_data, dict):
                        responses.update(resp_data.get("responses", resp_data))
            except Exception as e:
                logger.warning("Error reading responses.json in %s: %s", pack_dir, e)

        # 3. Intents (from intents.json)
        intents_data: dict[str, Any] = {}
        intents_file = pack_dir / "intents.json"
        if intents_file.is_file():
            try:
                with open(intents_file, "r", encoding="utf-8") as f:
                    ij = json.load(f)
                    intents_data = ij.get("intents", ij)
            except Exception as e:
                logger.warning("Error reading intents.json in %s: %s", pack_dir, e)

        # 4. Normalization (from normalization.json)
        norm_data: dict[str, Any] = {}
        norm_file = pack_dir / "normalization.json"
        if norm_file.is_file():
            try:
                with open(norm_file, "r", encoding="utf-8") as f:
                    norm_data = json.load(f)
            except Exception as e:
                logger.warning("Error reading normalization.json in %s: %s", pack_dir, e)

        # 5. Entities (from entities.json)
        entities_data: dict[str, Any] = {}
        entities_file = pack_dir / "entities.json"
        if entities_file.is_file():
            try:
                with open(entities_file, "r", encoding="utf-8") as f:
                    entities_data = json.load(f)
            except Exception as e:
                logger.warning("Error reading entities.json in %s: %s", pack_dir, e)

        # 6. Conversational (from conversational.json)
        conv_data: dict[str, Any] = {}
        conv_file = pack_dir / "conversational.json"
        if conv_file.is_file():
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    conv_data = json.load(f)
            except Exception as e:
                logger.warning("Error reading conversational.json in %s: %s", pack_dir, e)

        # 7. Rules hook (rules.py if present)
        rules_inst: Optional[BaseLanguageRules] = None
        rules_file = pack_dir / "rules.py"
        if rules_file.is_file():
            try:
                spec = importlib.util.spec_from_file_location(f"riata.languages.{code}.rules", rules_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "get_rules"):
                        rules_inst = mod.get_rules()
                    elif hasattr(mod, "rules"):
                        rules_inst = mod.rules
            except Exception as e:
                logger.warning("Error loading rules.py from %s: %s", pack_dir, e)

        return LanguagePack(
            code=code,
            name=name,
            english_name=english_name,
            native_name=native_name,
            direction=direction,
            version=version,
            script_pattern=script_pattern,
            responses=responses,
            intents=intents_data,
            normalization=norm_data,
            entities=entities_data,
            conversational=conv_data,
            rules=rules_inst,
        )

    def register(self, pack: LanguagePack) -> None:
        """Register a language pack in the registry."""
        if not pack.code:
            raise InvalidLanguagePackError("Language pack code cannot be empty")
        self._packs[pack.code] = pack
        logger.debug("Registered language pack: %s (%s)", pack.code, pack.name)

    def get(self, code: str) -> LanguagePack:
        """Retrieve a language pack by code or fallback safely."""
        if code in self._packs:
            return self._packs[code]
        # Common fallbacks if present
        if "en" in self._packs:
            return self._packs["en"]
        if "fa" in self._packs:
            return self._packs["fa"]
        if self._packs:
            return next(iter(self._packs.values()))
        # Empty fallback pack
        return LanguagePack(
            code=code,
            name=code,
            english_name=code,
            direction="ltr",
            version="0.1.1",
        )

    def has(self, code: str) -> bool:
        """Check if language code is registered."""
        return code in self._packs

    def get_supported_codes(self) -> list[str]:
        """Return list of registered language codes."""
        return list(self._packs.keys())

    def get_available_languages(self) -> list[tuple[str, str, str]]:
        """Return list of (code, name, direction) tuples."""
        return [(p.code, p.name, p.direction) for p in self._packs.values()]


_GLOBAL_REGISTRY: Optional[LanguageRegistry] = None


def get_language_registry() -> LanguageRegistry:
    """Retrieve the global LanguageRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = LanguageRegistry()
    return _GLOBAL_REGISTRY
