"""The page object base class.

A page object is the vocabulary of one screen: it turns "fill the field whose data-test is
username, then click login-button" into ``login.entrar_como(usuario, clave)``. Tests then read
as business intent, and when the markup changes there is exactly one place to fix.

:class:`BasePage` talks to the abstract :class:`~automation_framework.core.engine.Engine`, never
to Playwright or pywinauto. That is what will let the desktop suites of Fase 5 reuse this class
unchanged — a ``ScreenObject`` would be the same idea with the same base.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

from automation_framework.core.element import ElementState
from automation_framework.core.exceptions import AutomationError, PageNotLoadedError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from automation_framework.core.element import Element
    from automation_framework.core.engine import Engine
    from automation_framework.core.locator import Locator


class BasePage(ABC):
    """Base for every page object.

    Subclasses declare their locators as class-level constants and expose methods named after
    what a user does, not after what the automation does.

    Args:
        engine: The started engine driving the application under test.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------- identidad ---

    @property
    @abstractmethod
    def marker(self) -> Locator:
        """A locator that is present **only** when this screen is on display.

        The single thing a subclass must provide. It is what makes "am I on the right page?"
        answerable, and it should be something structural — a heading, a container — rather
        than the first control the test happens to use.
        """

    @property
    def name(self) -> str:
        """Human-readable name for messages. The class name unless a subclass says otherwise."""
        return type(self).__name__

    @property
    def engine(self) -> Engine:
        """The engine this page drives.

        Exposed for the operations the abstract contract does not cover — web navigation, for
        instance. Reaching for it from a test is a sign that the page object is missing a
        method, not that it needs the engine.
        """
        return self._engine

    def __repr__(self) -> str:
        return f"{type(self).__name__}(marker={self.marker})"

    # -------------------------------------------------------------------- búsqueda ---

    def find(self, locator: Locator) -> Element:
        """A lazy handle to the first element matching ``locator``."""
        return self._engine.find(locator)

    def find_all(self, locator: Locator) -> Sequence[Element]:
        """One handle per element matching ``locator``, resolved now."""
        return self._engine.find_all(locator)

    # ------------------------------------------------------------------ componentes ---

    def component[C](self, factory: Callable[[Element], C], locator: Locator) -> C:
        """Build one component anchored at the first element matching ``locator``."""
        return factory(self.find(locator))

    def components[C](self, factory: Callable[[Element], C], locator: Locator) -> Sequence[C]:
        """Build one component per element matching ``locator``.

        The natural way to describe a list of repeated blocks — rows, cards, results — where
        each one answers questions about itself instead of the page holding a locator per
        column per row.
        """
        return [factory(element) for element in self.find_all(locator)]

    # ----------------------------------------------------------------------- carga ---

    def is_loaded(self) -> bool:
        """Whether the screen is on display right now. Returns immediately.

        A question, so it never raises: a page object that blows up when asked "are you
        there?" cannot be used to choose between two possible screens.
        """
        try:
            return self.find(self.marker).is_visible()
        except AutomationError:
            return False

    def wait_until_loaded(self, *, timeout: float | None = None) -> Self:
        """Block until the screen is on display. Returns ``self`` so it chains.

        Call it after whatever navigates here. Without it the first interaction races the
        transition, and the test fails pointing at an element instead of at the navigation
        that never happened.

        Raises:
            PageNotLoadedError: The marker never appeared.
        """
        budget = self._engine.timeout if timeout is None else timeout
        try:
            self.find(self.marker).wait_for(ElementState.VISIBLE, timeout=budget)
        except AutomationError as error:
            raise PageNotLoadedError(self.name, self.marker, timeout=budget) from error
        return self
