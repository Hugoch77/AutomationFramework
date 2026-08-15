"""Web engine, backed by Playwright.

Importing this package registers the engine under the name ``"web"``, which is what lets
``create_engine("web")`` work without ``core`` ever knowing Playwright exists.
"""

from automation_framework.core.registry import is_registered, register_engine
from automation_framework.engines.web.element import WebElement
from automation_framework.engines.web.engine import PlaywrightEngine
from automation_framework.engines.web.locators import ENGINE_NAME, WEB_CAPABILITIES, to_playwright

# Idempotente: importar el paquete dos veces (o recargarlo en tests) no debe reventar.
if not is_registered(ENGINE_NAME):
    register_engine(ENGINE_NAME, PlaywrightEngine)

__all__ = [
    "ENGINE_NAME",
    "WEB_CAPABILITIES",
    "PlaywrightEngine",
    "WebElement",
    "to_playwright",
]
