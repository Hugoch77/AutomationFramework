"""The web implementation of the element contract.

Only the six protected primitives are implemented here. Laziness, the auto-waiting policy and
the error reporting all come from :class:`~automation_framework.core.element.Element`.

Playwright errors are translated on the way out. If a `TimeoutError` from Playwright reached
a test, the abstraction would be leaking and suites would start catching engine-specific
exceptions — exactly what this framework exists to avoid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation_framework.core.element import Element
from automation_framework.core.exceptions import ElementError, ElementNotFoundError
from automation_framework.engines.web.locators import to_playwright

if TYPE_CHECKING:
    from playwright.sync_api import Locator as PlaywrightLocator
    from playwright.sync_api import Page

    from automation_framework.core.locator import Locator

DEFAULT_QUERY_TIMEOUT = 1.0
"""Seconds Playwright gets for a single read.

Reads are one-shot by contract: the retry loop lives in `Element`. Playwright's own
auto-waiting would otherwise stack on top of ours and a missing element would take
Playwright's 30s default plus our budget before failing.
"""


class WebElement(Element):
    """A handle to one element in a Playwright page."""

    def __init__(
        self,
        page: Page,
        locator: Locator,
        *,
        index: int = 0,
        timeout: float,
        poll_interval: float,
        query_timeout: float = DEFAULT_QUERY_TIMEOUT,
    ) -> None:
        super().__init__(locator, timeout=timeout, poll_interval=poll_interval)
        self._page = page
        self._index = index
        self._query_ms = query_timeout * 1000
        self._action_ms = timeout * 1000
        self._resolved: PlaywrightLocator | None = None

    @property
    def _target(self) -> PlaywrightLocator:
        """The Playwright locator, resolved once and reused.

        `nth` is always applied, even for the first match: without it a locator matching
        several elements trips Playwright's strict mode, and "the first one" is what the
        `find` contract promises.
        """
        if self._resolved is None:
            self._resolved = to_playwright(self._page, self._locator).nth(self._index)
        return self._resolved

    # ------------------------------------------------------------------ consultas ---

    def _exists(self) -> bool:
        try:
            return self._target.count() > 0
        except PlaywrightError:
            # Una navegación a mitad de consulta puede invalidar el contexto. Para el
            # contrato eso es simplemente "ahora mismo no está"; el bucle de espera reintenta.
            return False

    def _is_visible(self) -> bool:
        try:
            return self._target.is_visible(timeout=self._query_ms)
        except PlaywrightError:
            return False

    def _text(self) -> str:
        try:
            return self._target.inner_text(timeout=self._query_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator) from error

    def _attribute(self, name: str) -> str | None:
        try:
            return self._target.get_attribute(name, timeout=self._query_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator) from error

    def _value(self) -> str:
        try:
            return self._target.input_value(timeout=self._query_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator) from error
        except PlaywrightError as error:
            # Playwright rechaza input_value() sobre lo que no es un campo editable.
            raise ElementError(
                f"El elemento {self._locator} no tiene un valor editable; "
                "¿querías text() o attribute()?"
            ) from error

    # ------------------------------------------------------------------- acciones ---
    # Reciben el timeout completo del engine: las comprobaciones de accionabilidad de
    # Playwright (visible, estable, habilitado, recibe eventos) son valiosas y necesitan
    # margen. Nuestra espera previa sólo garantiza visibilidad.

    def _click(self) -> None:
        try:
            self._target.click(timeout=self._action_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator, timeout=self._action_ms / 1000) from error

    def _fill(self, text: str) -> None:
        try:
            self._target.fill(text, timeout=self._action_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator, timeout=self._action_ms / 1000) from error
