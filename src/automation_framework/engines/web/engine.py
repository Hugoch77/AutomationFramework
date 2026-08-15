"""The Playwright implementation of the engine contract.

Owns the browser → context → page chain. The guards (`is started?`, `is this strategy
supported?`) live in the base class, so what is left here is genuinely web-specific.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

from automation_framework.core.engine import Engine
from automation_framework.core.exceptions import ConfigurationError, EngineNotStartedError
from automation_framework.core.log import get_logger
from automation_framework.core.waits import DEFAULT_POLL_INTERVAL, DEFAULT_TIMEOUT
from automation_framework.engines.web.element import WebElement
from automation_framework.engines.web.locators import WEB_CAPABILITIES, to_playwright

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from playwright.sync_api import Browser, BrowserContext, Page, Playwright, ViewportSize

    from automation_framework.core.capabilities import Capabilities
    from automation_framework.core.element import Element
    from automation_framework.core.locator import Locator

log = get_logger(__name__)

SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")


class PlaywrightEngine(Engine):
    """Drives a web application through Playwright's synchronous API.

    Args:
        browser: One of ``chromium``, ``firefox`` or ``webkit``.
        headless: Run without a visible window. CI needs this on.
        base_url: Root for relative navigation, so page objects can say ``/inventory``.
        viewport: ``(width, height)`` in pixels, or ``None`` for Playwright's default.
        record_trace: Record a Playwright trace, retrievable with :meth:`save_trace`.
            Off by default because a trace costs time and disk on every single test.
    """

    def __init__(
        self,
        *,
        browser: str = "chromium",
        headless: bool = True,
        base_url: str | None = None,
        viewport: tuple[int, int] | None = None,
        record_trace: bool = False,
        test_id_attribute: str = "data-testid",
        timeout: float = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        super().__init__(timeout=timeout, poll_interval=poll_interval)
        if browser not in SUPPORTED_BROWSERS:
            raise ConfigurationError(
                f"Navegador desconocido: {browser!r}. Disponibles: {', '.join(SUPPORTED_BROWSERS)}."
            )
        self._browser_name = browser
        self._headless = headless
        self._base_url = base_url
        self._viewport = viewport
        self._record_trace = record_trace
        self._test_id_attribute = test_id_attribute

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def capabilities(self) -> Capabilities:
        return WEB_CAPABILITIES

    @property
    def page(self) -> Page:
        """The active Playwright page.

        Escape hatch for what the abstract contract does not cover. Using it from a test
        couples that test to Playwright, so keep it inside the web engine's own layer.

        Raises:
            EngineNotStartedError: The engine has not been started.
        """
        if self._page is None:
            raise EngineNotStartedError(self.name, "page")
        return self._page

    # ------------------------------------------------------------- ciclo de vida ---

    def _start(self) -> None:
        self._playwright = sync_playwright().start()
        # Global a Playwright, no al contexto: hay que fijarlo antes de crear nada.
        self._playwright.selectors.set_test_id_attribute(self._test_id_attribute)
        browser_type = getattr(self._playwright, self._browser_name)
        self._browser = browser_type.launch(headless=self._headless)

        viewport: ViewportSize | None = (
            {"width": self._viewport[0], "height": self._viewport[1]} if self._viewport else None
        )
        self._context = self._browser.new_context(base_url=self._base_url, viewport=viewport)
        self._context.set_default_timeout(self._timeout * 1000)

        if self._record_trace:
            self._context.tracing.start(screenshots=True, snapshots=True, sources=True)

        self._page = self._context.new_page()
        log.debug("engine web arrancado", browser=self._browser_name, headless=self._headless)

    def _stop(self) -> None:
        """Close everything in reverse order, tolerating a partial start.

        Teardown runs from a ``finally`` — and now also from a failed `start()` — so if it
        raised it would mask the failure that actually matters. Each step is closed
        independently and logged on error.

        The catch is deliberately `Exception` and not `PlaywrightError`: closing touches the
        filesystem and a pipe to the driver process, so an `OSError` is just as possible as a
        Playwright one, and it must not be the exception a test ends up reporting.
        """
        closers: list[tuple[str, Callable[[], None]]] = []
        if self._page is not None:
            closers.append(("page", self._page.close))
        if self._context is not None:
            closers.append(("context", self._context.close))
        if self._browser is not None:
            closers.append(("browser", self._browser.close))
        if self._playwright is not None:
            closers.append(("playwright", self._playwright.stop))

        for label, close in closers:
            try:
                close()
            except Exception as error:
                log.warning("fallo cerrando recurso del engine", recurso=label, error=str(error))

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    # ----------------------------------------------------------------- navegación ---

    def goto(self, url: str) -> None:
        """Navigate to ``url``, relative to ``base_url`` when one was configured.

        Web-specific on purpose. "Navigate" has no honest equivalent on the desktop side,
        and inventing a generic ``open()`` before the desktop engine exists would be
        guessing at a shape we cannot yet check. Fase 5 will say whether it is warranted.
        """
        self._require_started("goto")
        self.page.goto(url)

    # ------------------------------------------------------------------ primitivas ---

    def _find(self, locator: Locator) -> Element:
        return WebElement(
            self.page, locator, timeout=self._timeout, poll_interval=self._poll_interval
        )

    def _find_all(self, locator: Locator) -> Sequence[Element]:
        total = to_playwright(self.page, locator).count()
        return [
            WebElement(
                self.page,
                locator,
                index=index,
                timeout=self._timeout,
                poll_interval=self._poll_interval,
            )
            for index in range(total)
        ]

    def _screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)
        return path

    # --------------------------------------------------------------------- trazas ---

    def save_trace(self, path: Path) -> Path | None:
        """Write the recorded trace to ``path``.

        Returns ``None`` when tracing was not enabled, so a failure hook can call this
        unconditionally without having to know how the engine was configured.
        """
        if not self._record_trace or self._context is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        self._context.tracing.stop(path=str(path))
        # Detenida ya la traza, no habrá otra: evita que un segundo intento falle en Playwright.
        self._record_trace = False
        return path
