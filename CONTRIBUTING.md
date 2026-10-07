# Contributing to R.I.A.T.A

Welcome, and thank you for your interest in contributing to **R.I.A.T.A**!

**Maintainer & Project Owner:** Ali Kamrani ([MRThugh](https://github.com/MRThugh))

---

## 🎯 Contribution Principles for v0.2.0

1. **Stability Over Expansion:** Version 0.2.0 is focused on context-aware interaction, deterministic multi-step planning, security hardening, testing, and clean architecture.
2. **No Feature Bloat:** Please avoid submitting pull requests introducing Large Language Models (LLMs), autonomous agents, cloud assistants, or large external dependencies.
3. **Deterministic & Safe:** All contributions must preserve the deterministic nature and strict zero-shell execution security model of R.I.A.T.A.

---

## 🛠️ Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MRThugh/RIATA.git
   cd RIATA
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```

3. **Run the test suite:**
   ```bash
   pytest -v
   ```

---

## 🧪 Testing Guidelines

* Every change, bug fix, or capability enhancement **must include automated tests**.
* Ensure tests pass before opening a Pull Request:
  ```bash
  pytest -v --tb=short
  ```
* For UI components, write tests that run cleanly in offscreen mode.
* For security-sensitive code, include negative regression tests testing boundary bypasses.

---

## 🌐 Adding or Improving Language Packs

Language packs are located in `languages/<code >/`. To add a new language:
1. Create `languages/<code >/manifest.json`.
2. Define grammar in `intents.json`.
3. Provide character normalization rules in `normalization.json`.
4. Provide entity mappings in `entities.json`.
5. Localize responses in `responses.json`.
6. Add affirmations and cancellations in `conversational.json`.
7. Verify your language pack loads cleanly in `test_v011_language_extensibility.py`.

---

## 📝 Code Style & Guidelines

* **Python:** Follow PEP 8 and Python 3.10+ typing guidelines. Use type annotations (`str`, `tuple[str, ...]`, `Optional[...]`).
* **Subprocess Security:** Never use `shell=True` or pass concatenated shell strings.
* **Logging:** Use `app.core.logger.get_logger()`. Never log passwords, tokens, or private user files.
* **Commit Messages:** Use clear, descriptive commit messages.

Thank you for helping make R.I.A.T.A a reliable desktop assistant!
