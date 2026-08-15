"""The engine contract.

An engine owns the lifecycle of one application under test and knows how to turn a
:class:`~automation_framework.core.locator.Locator` into an
:class:`~automation_framework.core.element.Element`.

Like :class:`~automation_framework.core.element.Element`, it is split into a concrete public
API that holds the guard rails, and protected primitives that each technology implements.
An engine author never has to remember to check "am I started?" or "do I support this
strategy?" — those checks live here and run for everyone.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

from automation_framework.core.capabilities import Feature
from automation_framework.core.exceptions import (
    EngineError,
    EngineNotStartedError,
    UnsupportedOperationError,
    UnsupportedStrategyError,
)
from automation_framework.core.waits import DEFAULT_POLL_INTERVAL, DEFAULT_TIMEOUT

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from types import TracebackType

    from automation_framework.core.capabilities import Capabilities
    from automation_framework.core.element import Element
    from automation_framework.core.locator import Locator, Strategy


class Engine(ABC):
    """Drives one application under test.

    Use it as a context manager so teardown happens even when a test blows up::

        with create_engine("web") as engine:
            engine.find(SEARCH_BOX).fill("notepad")
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._started = False

    # ---------------------------------------------------------------- descripción ---

    @property
    @abstractmethod
    def capabilities(self) -> Capabilities:
        """What this engine can resolve and what optional features it provides."""

    @property
    def name(self) -> str:
        """Short name of the engine, used in errors and logs."""
        return self.capabilities.name

    @property
    def is_started(self) -> bool:
        """Whether :meth:`start` has run and :meth:`stop` has not."""
        return self._started

    @property
    def timeout(self) -> float:
        """Default wait budget handed to the elements this engine creates."""
        return self._timeout

    @property
    def poll_interval(self) -> float:
        """Default poll interval handed to the elements this engine creates."""
        return self._poll_interval

    def __repr__(self) -> str:
        state = "arrancado" if self._started else "parado"
        return f"{type(self).__name__}(name={self.name!r}, {state})"

    # ----------------------------------------------------------------- primitivas ---
    # Lo único que implementa un engine concreto.

    @abstractmethod
    def _start(self) -> None:
        """Launch or attach to the application."""

    @abstractmethod
    def _stop(self) -> None:
        """Release every resource. Must tolerate a partially started engine."""

    @abstractmethod
    def _find(self, locator: Locator) -> Element:
        """Build a lazy handle for the first element matching ``locator``."""

    @abstractmethod
    def _find_all(self, locator: Locator) -> Sequence[Element]:
        """Resolve ``locator`` now and return a handle per match.

        Unlike :meth:`_find` this cannot be lazy: the caller is asking how many there are.
        """

    @abstractmethod
    def _screenshot(self, path: Path) -> Path:
        """Write an image of the application to ``path`` and return it."""

    # ----------------------------------------------------------- ciclo de vida ---

    def start(self) -> Self:
        """Launch the application. Returns ``self`` so it chains.

        Raises:
            EngineError: Already started. Almost always a fixture-scope mistake, so it is
                reported rather than silently ignored.
        """
        if self._started:
            raise EngineError(
                f"El engine {self.name!r} ya está arrancado. "
                "Revisa el scope de la fixture: probablemente se está arrancando dos veces."
            )
        self._start()
        self._started = True
        return self

    def stop(self) -> None:
        """Release everything. Safe to call more than once, and on a never-started engine.

        Teardown runs from ``finally`` blocks, where raising would mask the original failure.
        """
        if not self._started:
            return
        try:
            self._stop()
        finally:
            self._started = False

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

    # -------------------------------------------------------------------- búsqueda ---

    def find(self, locator: Locator) -> Element:
        """Return a lazy handle to the first element matching ``locator``.

        Does not touch the application: the lookup happens on first interaction.

        Raises:
            EngineNotStartedError: The engine has not been started.
            UnsupportedStrategyError: This engine cannot resolve that kind of locator.
        """
        self._require_started("find")
        self._require_supported(locator)
        return self._find(locator)

    def find_all(self, locator: Locator) -> Sequence[Element]:
        """Resolve ``locator`` now and return one handle per match, possibly empty.

        Raises:
            EngineNotStartedError: The engine has not been started.
            UnsupportedStrategyError: This engine cannot resolve that kind of locator.
        """
        self._require_started("find_all")
        self._require_supported(locator)
        return self._find_all(locator)

    def supports(self, strategy: Strategy) -> bool:
        """Whether this engine can resolve locators built with ``strategy``."""
        return self.capabilities.supports(strategy)

    def has_feature(self, feature: Feature) -> bool:
        """Whether this engine provides ``feature``."""
        return self.capabilities.has(feature)

    # -------------------------------------------------------------------- captura ---

    def screenshot(self, path: Path) -> Path:
        """Capture the application to ``path``.

        Raises:
            EngineNotStartedError: The engine has not been started.
            UnsupportedOperationError: This engine cannot take screenshots.
        """
        self._require_started("screenshot")
        self._require_feature(Feature.SCREENSHOT, "screenshot")
        return self._screenshot(path)

    # -------------------------------------------------------------------- guardas ---

    def _require_started(self, operation: str) -> None:
        if not self._started:
            raise EngineNotStartedError(self.name, operation)

    def _require_supported(self, locator: Locator) -> None:
        if not self.capabilities.supports(locator.strategy):
            raise UnsupportedStrategyError(
                self.name, locator.strategy, self.capabilities.strategies
            )

    def _require_feature(self, feature: Feature, operation: str) -> None:
        if not self.capabilities.has(feature):
            raise UnsupportedOperationError(self.name, operation)
