from __future__ import annotations

from typing import Literal


SupportedLocale = Literal["en", "es", "fr"]

DEFAULT_LOCALE: SupportedLocale = "en"
SUPPORTED_LOCALES: tuple[SupportedLocale, ...] = ("en", "es", "fr")


def is_supported_locale(value: object) -> bool:
    return isinstance(value, str) and value in SUPPORTED_LOCALES


def resolve_effective_locale(preferred_locale: object | None) -> SupportedLocale:
    """Return a safe platform locale until organisation inheritance is applied.

    The organisation resolver will call this with its resolved default when a
    user has no explicit preference. Keeping this fallback here prevents an
    invalid stored value from reaching UI or generation code.
    """

    if is_supported_locale(preferred_locale):
        return preferred_locale  # type: ignore[return-value]
    return DEFAULT_LOCALE
