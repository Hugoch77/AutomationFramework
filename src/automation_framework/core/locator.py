"""Technology-agnostic way of pointing at an element.

A :class:`Locator` is not a selector: it is an *intent* ("the element whose automation id is
``SearchBox``"). Each engine translates that intent into its own dialect — a CSS selector for
Playwright, a UI Automation criteria dict for pywinauto.

Locators are frozen and hashable on purpose, so a suite can declare them as module-level
constants next to the screen they belong to:

    SEARCH_BOX = Locator.automation_id("SearchBox", description="caja de búsqueda")
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Strategy(StrEnum):
    """How an element is identified.

    Not every engine supports every strategy; each one declares what it can resolve through
    its ``capabilities``. Asking for an unsupported strategy raises
    :class:`~automation_framework.core.exceptions.UnsupportedStrategyError` immediately.
    """

    # Understood by every engine.
    TEST_ID = "test_id"
    """Explicit hook left in the app for testing (``data-testid``, ``AutomationId``)."""

    TEXT = "text"
    """Visible text content. Brittle: it changes with locale and with copy edits."""

    NAME = "name"
    """Accessible name on web, ``Name`` property on UI Automation."""

    # Web-oriented.
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    CSS = "css"
    XPATH = "xpath"

    # Desktop-oriented (UI Automation).
    AUTOMATION_ID = "automation_id"
    CONTROL_TYPE = "control_type"
    CLASS_NAME = "class_name"

    def __repr__(self) -> str:
        return f"Strategy.{self.name}"


@dataclass(frozen=True, slots=True)
class Locator:
    """An engine-agnostic description of a single element.

    Args:
        strategy: How to identify the element.
        value: The value the strategy matches against.
        description: Human-readable label used in error messages and logs. Worth filling in:
            it is the difference between "no se encontró el elemento" and knowing which one.
        options: Extra hints for engines that need them (for example ``name`` when pairing
            with :attr:`Strategy.ROLE`). Excluded from equality so that locators stay usable
            as dictionary keys.
    """

    strategy: Strategy
    value: str
    description: str | None = None
    options: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("El valor de un Locator no puede estar vacío.")

    def __str__(self) -> str:
        label = self.description or self.value
        return f"{label!r} ({self.strategy.value}={self.value!r})"

    def with_options(self, **options: Any) -> Locator:
        """Return a copy carrying additional engine hints."""
        merged = {**self.options, **options}
        return Locator(self.strategy, self.value, self.description, merged)

    # -- Atajos de construcción -------------------------------------------------------
    # Existen para que las suites lean bien; toda la lógica está en el constructor.

    @classmethod
    def test_id(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.TEST_ID, value, description)

    @classmethod
    def text(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.TEXT, value, description)

    @classmethod
    def name(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.NAME, value, description)

    @classmethod
    def role(
        cls, value: str, *, name: str | None = None, description: str | None = None
    ) -> Locator:
        options: dict[str, Any] = {"name": name} if name is not None else {}
        return cls(Strategy.ROLE, value, description, options)

    @classmethod
    def css(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.CSS, value, description)

    @classmethod
    def xpath(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.XPATH, value, description)

    @classmethod
    def automation_id(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.AUTOMATION_ID, value, description)

    @classmethod
    def control_type(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.CONTROL_TYPE, value, description)

    @classmethod
    def class_name(cls, value: str, *, description: str | None = None) -> Locator:
        return cls(Strategy.CLASS_NAME, value, description)
