# R.I.A.T.A — Language Pack System
**Responsive Intent Automation & Task Assistant (v0.2.0)**  
**Author:** Ali Kamrani (MRThugh)  

---

## 1. Overview

R.I.A.T.A features an extensible **Language Registry** architecture. The core intent engine and executors are language-agnostic and consume Language Packs dynamically discovered from the `languages/` directory at runtime.

### Bundled Language Packs in v0.2.0:
* `fa` (Persian / فارسی) — Right-to-Left (RTL) layout
* `en` (English) — Left-to-Right (LTR) layout

---

## 2. Directory Layout of a Language Pack

Each language pack resides in its own folder:

```text
languages/
└── <code >/
    ├── manifest.json        # Pack metadata (id, name, text direction, version)
    ├── intents.json         # Regular expression patterns for intent matching
    ├── normalization.json   # Script-specific normalization and stop-word rules
    ├── entities.json        # Entity mappings (XDG folders, ordinals)
    ├── responses.json       # Localized response feedback templates
    ├── conversational.json  # Affirmations, cancellations, and vague patterns
    └── rules.py             # Optional custom Python rule evaluation hooks
```

---

## 3. Specification of Language Pack Files

### `manifest.json`
```json
{
  "id": "de",
  "code": "de",
  "name": "Deutsch",
  "native_name": "Deutsch",
  "english_name": "German",
  "direction": "ltr",
  "version": "0.1.1",
  "script_pattern": "[äöüÄÖÜß]"
}
```

### `intents.json`
```json
{
  "intents": {
    "OPEN_APPLICATION": {
      "patterns": [
        "^öffne\\s+(.+)$",
        "^starte\\s+(.+)$"
      ],
      "keywords": ["öffne", "starte"]
    }
  }
}
```

### `normalization.json`
```json
{
  "lowercase": true,
  "char_replacements": {
    "ß": "ss"
  },
  "particles_to_strip": ["bitte", "kannst du bitte"]
}
```

### `entities.json`
```json
{
  "folders": {
    "downloads": "Downloads",
    "dokumente": "Documents"
  },
  "ordinals": {
    "erste": 1,
    "zweite": 2
  }
}
```

### `responses.json`
```json
{
  "responses": {
    "greeting": "Hallo! Wie kann ich dir helfen?",
    "app_opened": "✓ {app_name} wurde erfolgreich geöffnet.",
    "app_not_found": "{app_name} wurde nicht auf dem System gefunden."
  }
}
```

### `conversational.json`
```json
{
  "confirmations": ["ja", "j", "sicher", "bestätigen"],
  "cancellations": ["nein", "abbrechen", "stopp"],
  "vague_patterns": ["^öffne\\s+das$"]
}
```

---

## 4. Security & Trusted Code Model for `rules.py`

Language packs can optionally include a `rules.py` file implementing custom linguistic heuristics:

```python
from app.languages.rules import BaseLanguageRules

class GermanLanguageRules(BaseLanguageRules):
    def post_process_entities(self, intent_name: str, entities: dict) -> dict:
        return entities

def get_rules() -> BaseLanguageRules:
    return GermanLanguageRules()
```

### ⚠️ Security Warning
`rules.py` is dynamic Python code loaded and executed within the application's runtime.
* **Trust Requirement:** Install language packs containing Python code **only from trusted sources**.
* **Fault Tolerance:** If a language pack's `rules.py` contains syntax errors, failed imports, or throws exceptions during execution, `LanguageRegistry` catches the error, logs a warning, and safely falls back to standard declarative JSON parsing without crashing R.I.A.T.A.
