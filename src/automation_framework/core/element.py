"""The element contract.

Elements are **lazy**: :meth:`~automation_framework.core.engine.Engine.find` hands back a handle
without touching the application. The lookup happens when you interact, which is what allows
locators to be declared as module-level constants and what makes auto-waiting possible.

The class is deliberately split in two halves:

* **Public methods** (``click``, ``fill``, ``text``, ...) carry the waiting policy. They are
  concrete and shared by every engine.
* **Protected primitives** (``_click``, ``_fill``, ``_text``, ...) are one-shot, no-waiting
  queries against the real technology. They are the *only* thing an engine implements.

That split is why adding an engine is cheap: the retry-and-wait logic that is easy to get wrong
is written once, here, and inherited for free.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Self, assert_never

from automation_framework.core.exceptions import ElementNotFoundError, WaitTimeoutError
from automation_framework.core.waits import DEFAULT_POLL_INTERVAL, DEFAULT_TIMEOUT, wait_until

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from automation_framework.core.locator import Locator


class ElementState(StrEnum):
    """A condition an element can be waited for."""

    PRESENT = "present"
    """Exists in the tree, visible or not."""

    VISIBLE = "visible"
    """Exists and is displayed to the user."""

    HIDDEN = "hidden"
    """Either absent, or present but not displayed."""

    ABSENT = "absent"
    """Not in the tree at all."""


class Element(ABC):
    """A lazy handle to a single element in the application under test."""

    def __init__(
        self,
        locator: Locator,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._locator = locator
        self._timeout = timeout
        self._poll_interval = poll_interval

    @property
    def locator(self) -> Locator:
        """The locator this handle was built from."""
        return self._locator

    @property
    def timeout(self) -> float:
        """Default wait budget, in seconds, for this handle.

        Public so that helpers built on top of the contract — assertions, page objects — can
        honour the engine's configured budget instead of hardcoding one of their own.
        """
        return self._timeout

    @property
    def poll_interval(self) -> float:
        """Delay between attempts while waiting, in seconds."""
        return self._poll_interval

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._locator})"

    # ------------------------------------------------------------------ primitivas ---
    # Lo único que implementa un engine. Consultas de un solo intento, sin esperas:
    # la política de espera vive en los métodos públicos de más abajo.

    @abstractmethod
    def _exists(self) -> bool:
        """Whether the element is in the tree right now."""

    @abstractmethod
    def _is_visible(self) -> bool:
        """Whether the element is displayed right now. ``False`` if it does not exist."""

    @abstractmethod
    def _text(self) -> str:
        """The element's current text content."""

    @abstractmethod
    def _attribute(self, name: str) -> str | None:
        """The element's current value for ``name``, or ``None`` if it has none."""

    @abstractmethod
    def _value(self) -> str:
        """The element's current editable value."""

    @abstractmethod
    def _click(self) -> None:
        """Click the element."""

    @abstractmethod
    def _fill(self, text: str) -> None:
        """Replace the element's value with ``text``."""

    @abstractmethod
    def _select(self, value: str) -> None:
        """Choose the option identified by ``value`` in a list of choices."""

    @abstractmethod
    def _find_child(self, locator: Locator) -> Element:
        """Build a lazy handle for the first descendant matching ``locator``."""

    @abstractmethod
    def _find_children(self, locator: Locator) -> Sequence[Element]:
        """Resolve ``locator`` inside this element now and return a handle per match."""

    # ------------------------------------------------------------------- consultas ---
    # Devuelven ya, sin esperar: preguntar "¿está?" y que la respuesta tarde diez
    # segundos en llegar sería una sorpresa desagradable.

    def exists(self) -> bool:
        """Whether the element is in the tree. Returns immediately."""
        return self._exists()

    def is_visible(self) -> bool:
        """Whether the element is displayed. Returns immediately."""
        return self._is_visible()

    # -------------------------------------------------------------------- acciones ---
    # Esperan a que el elemento esté en condiciones antes de actuar.

    def click(self, *, timeout: float | None = None) -> None:
        """Wait for the element to be visible, then click it."""
        self.wait_for(ElementState.VISIBLE, timeout=timeout)
        self._click()

    def fill(self, text: str, *, timeout: float | None = None) -> None:
        """Wait for the element to be visible, then replace its value with ``text``."""
        self.wait_for(ElementState.VISIBLE, timeout=timeout)
        self._fill(text)

    def select(self, value: str, *, timeout: float | None = None) -> None:
        """Wait for the element to be visible, then choose the ``value`` option.

        A dropdown is not a text field: typing into it does nothing, and ``fill`` either fails
        or silently misses. Both technologies treat choosing as its own operation —
        ``select_option`` in Playwright, the SelectionItem pattern in UI Automation — so it is
        a primitive rather than a special case of filling.

        Raises:
            ElementError: The element is not a list of choices, or has no such option.
        """
        self.wait_for(ElementState.VISIBLE, timeout=timeout)
        self._select(value)

    def text(self, *, timeout: float | None = None) -> str:
        """Wait for the element to be present, then read its text."""
        self.wait_for(ElementState.PRESENT, timeout=timeout)
        return self._text()

    def attribute(self, name: str, *, timeout: float | None = None) -> str | None:
        """Wait for the element to be present, then read the ``name`` attribute.

        Note this reads the *declared* attribute. For what the user typed into a field, use
        :meth:`value` — typing changes the DOM property, never the HTML attribute.
        """
        self.wait_for(ElementState.PRESENT, timeout=timeout)
        return self._attribute(name)

    def value(self, *, timeout: float | None = None) -> str:
        """Wait for the element to be present, then read its current editable value.

        Separate from :meth:`attribute` because ``attribute("value")`` returns the markup's
        declared value, which does not change when the user types. Both technologies model
        this distinctly — ``input_value()`` in Playwright, the Value pattern in UI Automation —
        so it earns a primitive of its own rather than a special case inside ``attribute``.

        Raises:
            ElementError: The element has no editable value (it is not a field).
        """
        self.wait_for(ElementState.PRESENT, timeout=timeout)
        return self._value()

    # -------------------------------------------------------------------- búsqueda ---
    # Búsqueda relativa: la misma consulta, acotada a este subárbol.

    def find(self, locator: Locator) -> Element:
        """A lazy handle to the first descendant matching ``locator``.

        This is what makes reusable components possible. Without it, the third row of a table
        can only be addressed with an XPath that encodes the whole page structure, and the
        same component cannot be pointed at two different tables on one screen.

        Both technologies model this natively — ``locator.locator()`` in Playwright,
        ``child_window()`` in UI Automation — which is why it earns a place in the contract
        rather than being emulated with cleverer selectors.
        """
        return self._find_child(locator)

    def find_all(self, locator: Locator) -> Sequence[Element]:
        """One handle per descendant matching ``locator``, resolved now."""
        return self._find_children(locator)

    # --------------------------------------------------------------------- esperas ---

    def wait_for(
        self,
        state: ElementState = ElementState.VISIBLE,
        *,
        timeout: float | None = None,
    ) -> Self:
        """Block until the element reaches ``state``.

        Returns ``self`` so waits can be chained onto a lookup.

        Raises:
            ElementNotFoundError: Waiting for ``PRESENT`` or ``VISIBLE`` and it never showed up.
            WaitTimeoutError: Waiting for ``HIDDEN`` or ``ABSENT`` and it never went away.
        """
        budget = self._timeout if timeout is None else timeout
        condition = self._condition_for(state)

        try:
            wait_until(
                condition,
                description=f"que el elemento {self._locator} esté en estado {state.value!r}",
                timeout=budget,
                poll_interval=self._poll_interval,
            )
        except WaitTimeoutError as error:
            # "No apareció" es un diagnóstico mucho más útil que "se agotó la espera",
            # y es de lejos el fallo más frecuente en una suite.
            if state in (ElementState.PRESENT, ElementState.VISIBLE):
                raise ElementNotFoundError(self._locator, timeout=budget) from error
            raise

        return self

    def _condition_for(self, state: ElementState) -> Callable[[], bool]:
        match state:
            case ElementState.PRESENT:
                return self._exists
            case ElementState.VISIBLE:
                return self._is_visible
            case ElementState.HIDDEN:
                return lambda: not self._is_visible()
            case ElementState.ABSENT:
                return lambda: not self._exists()
            case _:  # pragma: no cover - inalcanzable, pero mypy verifica la exhaustividad
                # Sin esto, añadir un ElementState nuevo devolvería None en silencio y el
                # fallo aparecería dentro de wait_until, lejos de la causa.
                assert_never(state)
