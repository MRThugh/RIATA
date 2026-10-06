"""Languages package for R.I.A.T.A."""

from app.languages.detector import (
    LanguageDetector,
    detect_language,
    get_language_detector,
)
from app.languages.loader import (
    LanguageLoader,
    LanguagePack,
    get_language_loader,
)

__all__ = [
    "LanguageDetector",
    "detect_language",
    "get_language_detector",
    "LanguageLoader",
    "LanguagePack",
    "get_language_loader",
]
