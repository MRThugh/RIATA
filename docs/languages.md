# R.I.A.T.A — Language Pack System
**Responsive Intent Automation & Task Assistant (v0.1.0)**  
**Author:** Ali Kamrani (MRThugh)  

---

## 1. Overview

R.I.A.T.A features a modular language pack architecture designed for effortless internationalization. Adding a new language requires zero modifications to core execution modules.

Default supported language packs in v0.1.0:
- `fa` (Persian / فارسی) — Right-to-Left (RTL)
- `en` (English) — Left-to-Right (LTR)

---

## 2. Directory Layout of a Language Pack

To add a new language pack (for example, German `de` or French `fr`), create:

```text
languages/
└── de/
    ├── language.json        # Metadata, text direction, localized responses
    ├── intents.json         # Regex patterns and keywords for intent recognition
    └── normalization.json   # Character sanitization, contractions, stop words
```

The `LanguageLoader` automatically scans `languages/` at runtime and registers new packs without restarting or modifying code.

---

## 3. File Specifications

### `language.json`
```json
{
  "code": "de",
  "name": "Deutsch",
  "english_name": "German",
  "direction": "ltr",
  "version": "0.1.0",
  "responses": {
    "greeting": "Hallo! Wie kann ich dir helfen?",
    "app_opened": "✓ {app_name} wurde erfolgreich geöffnet.",
    "app_not_found": "{app_name} wurde nicht auf dem System gefunden.",
    "unknown_intent": "Ich habe nicht verstanden, was du tun möchtest."
  }
}
```

### `intents.json`
```json
{
  "intents": {
    "OPEN_APPLICATION": {
      "patterns": [
        "^(?:öffne|starte)\\s+(.+)$"
      ],
      "keywords": ["öffne", "starte"]
    }
  }
}
```

### `normalization.json`
```json
{
  "char_replacements": {
    "ß": "ss"
  },
  "particles_to_strip": [
    "bitte",
    "kannst du"
  ]
}
```
