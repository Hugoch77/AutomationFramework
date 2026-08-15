"""Configuration, layered so CI can change behaviour without touching code.

Precedence, lowest to highest: field defaults → ``.env`` file → environment variables.
Everything is namespaced under ``AF_``, and nested values use a double underscore::

    AF_ENGINE=desktop
    AF_HEADLESS=false
    AF_TIMEOUTS__DEFAULT=30
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from automation_framework.core.exceptions import ConfigurationError
from automation_framework.core.waits import DEFAULT_POLL_INTERVAL, DEFAULT_TIMEOUT

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


class Timeouts(BaseModel):
    """Wait budgets, in seconds.

    Separate knobs on purpose: launching an application is slow and unpredictable, while
    waiting for a button should be quick. One shared number would have to accommodate the
    worst case and would make every other failure take that long to surface.
    """

    default: float = Field(default=DEFAULT_TIMEOUT, gt=0)
    """Waiting for an element to reach a state."""

    poll_interval: float = Field(default=DEFAULT_POLL_INTERVAL, gt=0)
    """Delay between attempts while waiting."""

    startup: float = Field(default=30.0, gt=0)
    """Launching or attaching to the application under test."""


class Viewport(BaseModel):
    """Window size for engines that have one."""

    width: int = Field(default=1280, gt=0)
    height: int = Field(default=720, gt=0)

    def as_tuple(self) -> tuple[int, int]:
        return (self.width, self.height)


class Settings(BaseSettings):
    """Everything the framework reads from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="AF_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    engine: str = "web"
    """Name the registry is asked for when no engine is specified."""

    headless: bool = True
    """Run without a visible UI where the engine supports it. CI needs this on."""

    browser: str = "chromium"
    """Which browser the web engine drives.

    Deliberately not validated here: the list of valid browsers is Playwright's knowledge,
    and `core` does not get to know that Playwright exists. The web engine validates it and
    raises `ConfigurationError` with the actual options.
    """

    viewport: Viewport = Field(default_factory=Viewport)

    test_id_attribute: str = "data-testid"
    """Which attribute :attr:`Strategy.TEST_ID` reads.

    Configurable because real applications rarely use the default: `data-test`, `data-qa` and
    `data-cy` are all common. Without this, the most robust strategy would be unusable on most
    apps and suites would fall back to brittle CSS.
    """

    trace: bool = False
    """Record an engine trace. Off by default — it costs time and disk on every test."""

    base_url: str | None = None
    """Root URL for web suites. Page objects build their paths from it."""

    artifacts_dir: Path = Path("artifacts")
    """Where screenshots, traces and reports are written."""

    capture_on_failure: bool = True
    """Collect evidence automatically when a test fails."""

    log_level: str = "INFO"
    log_json: bool = False
    """Emit JSON lines instead of human-readable logs. Turn on in CI."""

    timeouts: Timeouts = Field(default_factory=Timeouts)

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, value: str) -> str:
        if value not in LOG_LEVELS:
            raise ValueError(f"Nivel de log inválido: {value!r}. Válidos: {', '.join(LOG_LEVELS)}.")
        return value

    @field_validator("engine")
    @classmethod
    def _check_engine(cls, value: str) -> str:
        normalised = value.strip().lower()
        if not normalised:
            raise ValueError("El nombre del engine no puede estar vacío.")
        return normalised


ENV_PREFIX = "AF_"


def _check_for_unknown_variables() -> None:
    """Reject ``AF_*`` variables that map to no field.

    pydantic-settings silently ignores them, which turns ``AF_HEADLES=false`` into a setting
    that looks applied and is not — the kind of bug that costs an afternoon. Only the real
    environment is checked; a ``.env`` file is a local convenience, the environment is what
    CI actually uses.
    """
    known = set(Settings.model_fields)
    unknown = sorted(
        name
        for name in os.environ
        if name.startswith(ENV_PREFIX)
        # Los valores anidados llegan como AF_TIMEOUTS__DEFAULT: sólo cuenta el primer tramo.
        and name.removeprefix(ENV_PREFIX).split("__")[0].lower() not in known
    )
    if unknown:
        raise ConfigurationError(
            f"Variables de entorno desconocidas: {', '.join(unknown)}. "
            f"Ajustes válidos: {', '.join(sorted(known))}."
        )


def load_settings(**overrides: object) -> Settings:
    """Build settings from the environment, applying ``overrides`` on top.

    Raises:
        ConfigurationError: Something in the environment is invalid or unrecognised. When it
            comes from validation, pydantic's report is kept as the cause since it names the
            exact field.
    """
    _check_for_unknown_variables()
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as error:
        raise ConfigurationError(f"Configuración inválida:\n{error}") from error


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The process-wide settings, read once.

    Cached because configuration should not change mid-run: a suite where half the tests read
    one timeout and half another is not reproducible. Tests that need a different value call
    :func:`reset_settings` first.
    """
    return load_settings()


def reset_settings() -> None:
    """Drop the cached settings so the next :func:`get_settings` re-reads the environment."""
    get_settings.cache_clear()
