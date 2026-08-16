"""Translation from the framework's `Locator` to a Playwright locator.

This module is the entire reason `core` can stay technology-agnostic: an *intent*
("the element with test id `search-box`") becomes whatever Playwright understands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.exceptions import UnsupportedStrategyError
from automation_framework.core.locator import Strategy

if TYPE_CHECKING:
    from playwright.sync_api import Locator as PlaywrightLocator
    from playwright.sync_api import Page

    from automation_framework.core.locator import Locator

ENGINE_NAME = "web"

WEB_CAPABILITIES = Capabilities.of(
    ENGINE_NAME,
    strategies={
        Strategy.TEST_ID,
        Strategy.ROLE,
        Strategy.TEXT,
        Strategy.LABEL,
        Strategy.PLACEHOLDER,
        Strategy.CSS,
        Strategy.XPATH,
    },
    features={
        Feature.SCREENSHOT,
        Feature.TRACING,
        Feature.VIDEO,
        Feature.MULTIPLE_WINDOWS,
    },
)
"""What the web engine can resolve.

`Strategy.NAME` is deliberately absent. It means "accessible name", and Playwright cannot
address that on its own — an accessible name is only meaningful paired with a role. Use
`Strategy.ROLE` with the `name` option, or `Strategy.LABEL`. Declaring it and then guessing
would produce locators that silently match the wrong element.

The desktop strategies (`AUTOMATION_ID`, `CONTROL_TYPE`, `CLASS_NAME`) are absent for the
obvious reason: they belong to UI Automation.
"""


def to_playwright(scope: Page | PlaywrightLocator, locator: Locator) -> PlaywrightLocator:
    """Resolve `locator` against `scope`.

    `scope` is the page for a normal lookup, or another locator when searching inside an
    element. Playwright gives both the same query methods, so relative search needs no second
    translation — the one below works either way.

    Nothing is queried here — Playwright locators are lazy too, which is what makes the
    framework's laziness map onto this engine without any bookkeeping of our own.

    Raises:
        UnsupportedStrategyError: The web engine cannot express that strategy.
    """
    if not WEB_CAPABILITIES.supports(locator.strategy):
        raise UnsupportedStrategyError(ENGINE_NAME, locator.strategy, WEB_CAPABILITIES.strategies)

    options = locator.options
    match locator.strategy:
        case Strategy.TEST_ID:
            return scope.get_by_test_id(locator.value)
        case Strategy.ROLE:
            # `name` afina el rol con el nombre accesible; `exact` decide si es coincidencia
            # literal. Se pasan sólo si vienen, para no imponer defaults distintos a los
            # de Playwright.
            role_options = {key: options[key] for key in ("name", "exact") if key in options}
            return scope.get_by_role(locator.value, **role_options)  # type: ignore[arg-type]
        case Strategy.TEXT:
            return scope.get_by_text(locator.value, exact=bool(options.get("exact", False)))
        case Strategy.LABEL:
            return scope.get_by_label(locator.value, exact=bool(options.get("exact", False)))
        case Strategy.PLACEHOLDER:
            return scope.get_by_placeholder(locator.value)
        case Strategy.CSS:
            return scope.locator(locator.value)
        case Strategy.XPATH:
            # El prefijo explícito evita depender de la heurística de Playwright, que sólo
            # reconoce el XPath cuando empieza por "//" o "..".
            return scope.locator(f"xpath={locator.value}")
        case _:  # pragma: no cover - las capabilities ya filtraron el resto
            raise UnsupportedStrategyError(
                ENGINE_NAME, locator.strategy, WEB_CAPABILITIES.strategies
            )
