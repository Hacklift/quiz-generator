"""ISO 639 languages are selectable; en/es/fr ship with bundled UI fallbacks."""
import json
from pathlib import Path
from typing import Annotated
from pydantic import AfterValidator

LANGUAGES = json.loads(Path(__file__).with_name("languages.json").read_text())
SUPPORTED_LOCALES = frozenset(item["code"] for item in LANGUAGES)
LANGUAGE_NAMES = {item["code"]: item["name"] for item in LANGUAGES}
FALLBACK_LOCALES = ("en", "es", "fr")
DEFAULT_LOCALE = "en"


def is_supported_locale(value: object) -> bool:
    return isinstance(value, str) and value in SUPPORTED_LOCALES


def validate_locale(value: str) -> str:
    if not is_supported_locale(value):
        raise ValueError("Select a language from the ISO 639 language registry")
    return value


SupportedLocale = Annotated[str, AfterValidator(validate_locale)]


def resolve_effective_locale(preferred_locale: object | None) -> str:
    return preferred_locale if is_supported_locale(preferred_locale) else DEFAULT_LOCALE
