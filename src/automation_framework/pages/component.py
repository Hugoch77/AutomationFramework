"""Reusable blocks of a screen.

A component is a page object anchored at an element instead of at the whole screen: a row of a
table, a product card, a navbar, a modal. Every lookup it makes is scoped to that anchor, which
is what lets the same class describe the third row and the tenth, or two different tables on
one page, without any of its locators knowing where on the screen it sits.

That scoping is the entire difference between a component and a namespace full of locators, and
it rests on :meth:`~automation_framework.core.element.Element.find` being part of the contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from automation_framework.core.element import ElementState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from automation_framework.core.element import Element
    from automation_framework.core.locator import Locator


class Component:
    """A block of a screen, anchored at ``root``.

    Subclasses declare their locators **relative to the root** and expose methods named after
    what the block does. Args:
        root: The element the component hangs from.
    """

    def __init__(self, root: Element) -> None:
        self._root = root

    @property
    def root(self) -> Element:
        """The anchor element. Useful for waiting on the block as a whole."""
        return self._root

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={self._root.locator})"

    # -------------------------------------------------------------------- búsqueda ---

    def find(self, locator: Locator) -> Element:
        """A lazy handle to the first descendant of the root matching ``locator``."""
        return self._root.find(locator)

    def find_all(self, locator: Locator) -> Sequence[Element]:
        """One handle per descendant of the root matching ``locator``."""
        return self._root.find_all(locator)

    # ---------------------------------------------------------------------- estado ---

    def is_visible(self) -> bool:
        """Whether the block is on screen right now. Returns immediately."""
        return self._root.is_visible()

    def wait_until_visible(self, *, timeout: float | None = None) -> Self:
        """Block until the component is on screen. Returns ``self`` so it chains."""
        self._root.wait_for(ElementState.VISIBLE, timeout=timeout)
        return self
