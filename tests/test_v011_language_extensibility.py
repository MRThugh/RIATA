"""
Tests for R.I.A.T.A v0.1.1 Language Architecture & Extensibility.
Author: Ali Kamrani (MRThugh)

Verifies:
- Persian & English loading via LanguageRegistry
- Language-independent Intent generation
- Dynamically registering a third language (e.g., German 'de') without modifying core Python code.
"""

import pytest
from app.core.constants import INTENT_OPEN_APPLICATION, INTENT_OPEN_FOLDER
from app.engine.matcher import get_intent_parser
from app.engine.normalizer import get_normalizer
from app.languages.registry import (
    InvalidLanguagePackError,
    LanguagePack,
    LanguageRegistry,
    get_language_registry,
)


def test_language_registry_discovery():
    registry = get_language_registry()
    assert registry.has("fa")
    assert registry.has("en")

    fa_pack = registry.get("fa")
    assert fa_pack.code == "fa"
    assert fa_pack.direction == "rtl"
    assert fa_pack.version == "0.1.1"

    en_pack = registry.get("en")
    assert en_pack.code == "en"
    assert en_pack.direction == "ltr"


def test_invalid_language_pack_error():
    registry = LanguageRegistry()
    # Test that registering an empty-code pack raises error
    invalid_pack = LanguagePack(code="", name="Invalid", english_name="Invalid")
    with pytest.raises(InvalidLanguagePackError):
        registry.register(invalid_pack)


def test_hypothetical_third_language_without_core_modification():
    """
    EXTENSIBILITY PROOF:
    Add a German ('de') language pack dynamically at runtime with purely declarative
    configuration. Verify that:
    1. Normalization works
    2. Intent parsing matches OPEN_APPLICATION and OPEN_FOLDER
    3. Localized responses are formatted
    Without any core code modifications.
    """
    registry = get_language_registry()
    parser = get_intent_parser()
    normalizer = get_normalizer()

    german_pack = LanguagePack(
        code="de",
        name="Deutsch",
        native_name="Deutsch",
        english_name="German",
        direction="ltr",
        version="0.1.1",
        script_pattern=r"[äöüÄÖÜß]",
        responses={
            "app_opened": "✓ {app_name} wurde erfolgreich geöffnet.",
            "folder_opened": "✓ Ordner {folder_name} geöffnet.",
            "confirm_action": "Möchten Sie {action} wirklich ausführen? (ja / nein)",
        },
        intents={
            "OPEN_APPLICATION": {
                "patterns": [
                    r"^öffne\s+(?:die\s+App\s+)?(?P<app>.+)$",
                    r"^(?P<app>.+)\s+starten$",
                ]
            },
            "OPEN_FOLDER": {
                "patterns": [
                    r"^öffne\s+ordner\s+(?P<folder>.+)$",
                ]
            },
        },
        normalization={
            "lowercase": True,
            "char_replacements": {"ß": "ss"},
            "particles_to_strip": ["bitte", "kannst du bitte"],
        },
        entities={
            "folders": {
                "downloads": "Downloads",
                "dokumente": "Documents",
                "bilder": "Pictures",
            },
            "ordinals": {
                "erste": 1,
                "zweite": 2,
                "dritte": 3,
            },
            "application_patterns": [
                r"^öffne\s+(?:die\s+App\s+)?(?P<app>.+)$",
                r"^(?P<app>.+)\s+starten$",
            ],
            "application_prefixes_to_strip": ["die app"],
            "application_suffixes_to_strip": [],
            "folder_patterns": [
                r"^öffne\s+ordner\s+(?P<folder>.+)$",
            ],
        },
        conversational={
            "confirmations": ["ja", "j", "sicher", "bestätigen"],
            "cancellations": ["nein", "abbrechen", "stopp"],
            "vague_patterns": [r"^öffne\s+das$"],
        },
    )

    registry.register(german_pack)
    assert registry.has("de")

    # 1. Normalization
    norm = normalizer.normalize("Bitte öffne Firefox!", language="de")
    assert "firefox" in norm

    # 2. Intent matching with entity extraction
    intent = parser.parse("öffne firefox")
    assert intent.name == INTENT_OPEN_APPLICATION
    assert intent.entities.get("application") == "firefox"

    # 3. Folder extraction
    intent_folder = parser.parse("öffne ordner downloads")
    assert intent_folder.name == INTENT_OPEN_FOLDER
    assert intent_folder.entities.get("folder") == "Downloads"

    # 4. Response formatting
    resp = german_pack.get_response("app_opened", app_name="Firefox")
    assert resp == "✓ Firefox wurde erfolgreich geöffnet."

    # 5. Conversational confirmation check
    assert german_pack.is_confirmation("ja") is True
    assert german_pack.is_cancellation("nein") is True


def test_language_pack_with_faulty_rules_does_not_crash(tmp_path):
    """Verify that a language pack with broken/syntax-error rules.py loads gracefully without crashing."""
    import json
    from pathlib import Path
    pack_dir = tmp_path / "broken_lang"
    pack_dir.mkdir()

    manifest = {
        "code": "br",
        "name": "Broken",
        "english_name": "Broken",
        "direction": "ltr",
        "version": "0.1.1",
    }
    with open(pack_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    # Write a rules.py file with a syntax error
    with open(pack_dir / "rules.py", "w", encoding="utf-8") as f:
        f.write("def broken_syntax(:\n   invalid python code\n")

    registry = LanguageRegistry(languages_dir=tmp_path)
    # The broken pack should load its manifest without crashing the registry
    pack = registry.get("br")
    assert pack.code == "br"
    assert pack.rules is None

