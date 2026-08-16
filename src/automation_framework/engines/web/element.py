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
    from collections.abc import Sequence

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
        root: PlaywrightLocator | None = None,
    ) -> None:
        super().__init__(locator, timeout=timeout, poll_interval=poll_interval)
        self._page = page
        self._index = index
        self._query_ms = query_timeout * 1000
        self._action_ms = timeout * 1000
        self._query_timeout = query_timeout
        self._root = root
        self._resolved: PlaywrightLocator | None = None

    @property
    def _scope(self) -> Page | PlaywrightLocator:
        """Where lookups start: the page, or the ancestor this handle hangs from.

        Playwright locators expose the same query methods as the page, so the translation in
        `to_playwright` works unchanged against either — which is what keeps relative search
        from needing a second code path.
        """
        return self._page if self._root is None else self._root

    @property
    def _target(self) -> PlaywrightLocator:
        """The Playwright locator, resolved once and reused.

        `nth` is always applied, even for the first match: without it a locator matching
        several elements trips Playwright's strict mode, and "the first one" is what the
        `find` contract promises.
        """
        if self._resolved is None:
            self._resolved = to_playwright(self._scope, self._locator).nth(self._index)
        return self._resolved

    def _child(self, locator: Locator, index: int = 0) -> WebElement:
        """A handle scoped to this element's subtree."""
        return WebElement(
            self._page,
            locator,
            index=index,
            timeout=self._timeout,
            poll_interval=self._poll_interval,
            query_timeout=self._query_timeout,
            root=self._target,
        )

    def _failure(self, operation: str, error: PlaywrightError) -> ElementError:
        """Turn a Playwright error into a framework one.

        A timeout means "it never showed up" and has its own exception. Everything else is a
        genuine failure of the operation — a navigation invalidating the execution context, a
        detached node, a closed page — and it must not reach a test as a Playwright type, or
        suites would start writing `except PlaywrightError` and the abstraction would be over.

        Only the first line of the message survives: Playwright appends a full call log that
        buries the actual cause under its retry history.
        """
        detail = next(iter(str(error).splitlines()), "") or type(error).__name__
        return ElementError(f"Falló {operation} sobre el elemento {self._locator}: {detail}")

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
        except PlaywrightError as error:
            raise self._failure("la lectura del texto", error) from error

    def _attribute(self, name: str) -> str | None:
        try:
            return self._target.get_attribute(name, timeout=self._query_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator) from error
        except PlaywrightError as error:
            raise self._failure(f"la lectura del atributo {name!r}", error) from error

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
        except PlaywrightError as error:
            raise self._failure("el clic", error) from error

    def _fill(self, text: str) -> None:
        try:
            self._target.fill(text, timeout=self._action_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator, timeout=self._action_ms / 1000) from error
        except PlaywrightError as error:
            raise self._failure("el rellenado", error) from error

    def _select(self, value: str) -> None:
        try:
            self._target.select_option(value, timeout=self._action_ms)
        except PlaywrightTimeoutError as error:
            raise ElementNotFoundError(self._locator, timeout=self._action_ms / 1000) from error
        except PlaywrightError as error:
            # Playwright rechaza select_option sobre lo que no es un <select>, y también
            # cuando el <select> no tiene esa opción: ambas cosas son un error del test.
            raise self._failure(f"la selección de {value!r}", error) from error

    # ------------------------------------------------------------------- búsqueda ---

    def _find_child(self, locator: Locator) -> WebElement:
        return self._child(locator)

    def _find_children(self, locator: Locator) -> Sequence[WebElement]:
        try:
            total = to_playwright(self._target, locator).count()
        except PlaywrightError as error:
            raise self._failure(f"la búsqueda de {locator}", error) from error
        return [self._child(locator, index) for index in range(total)]
