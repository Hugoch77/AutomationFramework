"""An engine backed by a dictionary instead of an application.

:class:`FakeEngine` exists to answer one question early: *are the core contracts actually
implementable?* If writing this against ``Engine`` and ``Element`` feels awkward, the
abstractions are wrong — and it is far cheaper to discover that here than halfway through
wiring up Playwright.

It also gives the framework's own tests something to drive that has no browser, no window
and no timing: element states can be scripted (``appear_after``) so that waiting behaviour is
covered deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.element import Element
from automation_framework.core.engine import Engine
from automation_framework.core.exceptions import ElementError
from automation_framework.core.locator import Strategy

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from automation_framework.core.locator import Locator

FAKE_CAPABILITIES = Capabilities.of(
    "fake",
    # Acepta todas las estrategias a propósito: este engine no está para probar
    # restricciones de capacidades, sino el resto del contrato. Los tests que necesitan
    # un engine limitado se construyen uno a medida.
    strategies=frozenset(Strategy),
    features=frozenset({Feature.SCREENSHOT, Feature.MULTIPLE_WINDOWS, Feature.ELEMENT_TREE_DUMP}),
)


@dataclass
class FakeNode:
    """One scripted element in the fake application."""

    text: str = ""
    visible: bool = True
    attributes: dict[str, str] = field(default_factory=dict)

    value: str = ""
    """Current editable content, the equivalent of what a user typed into a field."""

    editable: bool = True
    """Whether the node has a value at all. Set to False to model a non-field element."""

    appear_after: int = 0
    """Number of lookups to answer "not there yet" before the node starts existing.

    This is how waiting is tested without real time passing.
    """

    lookups: int = 0
    """How many times this node has been queried. Useful for asserting on polling."""

    children: dict[Locator, list[FakeNode]] = field(default_factory=dict)
    """Nodes reachable only through this one, so relative search has something to walk."""

    options: tuple[str, ...] = ()
    """Choices this node offers, for modelling a dropdown.

    Empty means the node is **not** a list of choices, and selecting on it raises — the same
    thing the web engine does on an element that is not a ``<select>``.
    """

    def exists(self) -> bool:
        """Answer whether the node is in the tree, honouring ``appear_after``."""
        self.lookups += 1
        return self.lookups > self.appear_after

    def add_child(
        self,
        locator: Locator,
        *,
        text: str = "",
        visible: bool = True,
        attributes: dict[str, str] | None = None,
        value: str = "",
        editable: bool = True,
        appear_after: int = 0,
        options: tuple[str, ...] = (),
    ) -> FakeNode:
        """Script a descendant of this node and return it."""
        node = FakeNode(
            text=text,
            visible=visible,
            attributes=dict(attributes or {}),
            value=value,
            editable=editable,
            appear_after=appear_after,
            options=options,
        )
        self.children.setdefault(locator, []).append(node)
        return node


class FakeElement(Element):
    """A handle into :class:`FakeEngine`'s dictionary."""

    def __init__(
        self,
        engine: FakeEngine,
        locator: Locator,
        index: int = 0,
        parent: FakeElement | None = None,
    ) -> None:
        super().__init__(locator, timeout=engine.timeout, poll_interval=engine.poll_interval)
        self._engine = engine
        self._index = index
        self._parent = parent

    def _container(self) -> dict[Locator, list[FakeNode]] | None:
        """Where this handle looks itself up: the whole tree, or its parent's children.

        Resolved on each query rather than at construction, because a child handle has to stay
        as lazy as any other — its parent may not exist yet when the handle is created.
        """
        if self._parent is None:
            return self._engine.nodes
        parent = self._parent._node()
        return parent.children if parent is not None else None

    def _node(self) -> FakeNode | None:
        container = self._container()
        if container is None:
            return None
        nodes = container.get(self._locator, [])
        if self._index >= len(nodes):
            return None
        return nodes[self._index]

    def _existing_node(self) -> FakeNode | None:
        node = self._node()
        if node is None or not node.exists():
            return None
        return node

    def _exists(self) -> bool:
        return self._existing_node() is not None

    def _is_visible(self) -> bool:
        node = self._existing_node()
        return node is not None and node.visible

    def _text(self) -> str:
        node = self._existing_node()
        return node.text if node else ""

    def _attribute(self, name: str) -> str | None:
        node = self._existing_node()
        return node.attributes.get(name) if node else None

    def _value(self) -> str:
        node = self._existing_node()
        if node is None:
            return ""
        if not node.editable:
            raise ElementError(
                f"El elemento {self._locator} no tiene un valor editable; "
                "¿querías text() o attribute()?"
            )
        return node.value

    def _click(self) -> None:
        self._engine.record("click", self._locator)

    def _fill(self, text: str) -> None:
        self._engine.record("fill", self._locator, text)
        node = self._node()
        if node is not None:
            node.value = text

    def _select(self, value: str) -> None:
        """Choose an option, refusing anything that is not a list of choices.

        A node with no ``options`` is not a dropdown, and selecting on it must fail here just
        as Playwright's ``select_option`` fails on a non-``<select>``. A double that is more
        permissive than the real engine is worse than no double: it green-lights unit tests
        that would break against a browser.

        Unlike ``_fill``, the event is recorded only once the selection actually applies —
        ``events`` is meant to show what the application received, and a rejected choice never
        reached it.
        """
        node = self._node()
        if node is None:
            return
        if not node.options:
            raise ElementError(
                f"El elemento {self._locator} no es una lista de opciones; ¿querías fill()?"
            )
        if value not in node.options:
            raise ElementError(
                f"El elemento {self._locator} no tiene la opción {value!r}; "
                f"tiene: {', '.join(node.options)}."
            )
        node.value = value
        self._engine.record("select", self._locator, value)

    def _find_child(self, locator: Locator) -> FakeElement:
        return FakeElement(self._engine, locator, parent=self)

    def _find_children(self, locator: Locator) -> Sequence[FakeElement]:
        node = self._node()
        total = len(node.children.get(locator, [])) if node is not None else 0
        return [FakeElement(self._engine, locator, index, parent=self) for index in range(total)]


class FakeEngine(Engine):
    """An :class:`Engine` whose application under test is a dictionary.

    Timeouts default to something small: a test that accidentally waits should fail fast
    instead of stalling the suite for ten seconds.
    """

    def __init__(self, *, timeout: float = 1.0, poll_interval: float = 0.001) -> None:
        super().__init__(timeout=timeout, poll_interval=poll_interval)
        self.nodes: dict[Locator, list[FakeNode]] = {}
        self.events: list[tuple[str, ...]] = []
        self.start_count = 0
        self.stop_count = 0

    @property
    def capabilities(self) -> Capabilities:
        return FAKE_CAPABILITIES

    # ---------------------------------------------------------- montaje del escenario ---

    def add(
        self,
        locator: Locator,
        *,
        text: str = "",
        visible: bool = True,
        attributes: dict[str, str] | None = None,
        value: str = "",
        editable: bool = True,
        appear_after: int = 0,
        options: tuple[str, ...] = (),
    ) -> FakeNode:
        """Script an element into the fake application and return it."""
        node = FakeNode(
            text=text,
            visible=visible,
            attributes=dict(attributes or {}),
            value=value,
            editable=editable,
            appear_after=appear_after,
            options=options,
        )
        self.nodes.setdefault(locator, []).append(node)
        return node

    def remove(self, locator: Locator) -> None:
        """Take every node registered under ``locator`` out of the tree."""
        self.nodes.pop(locator, None)

    def record(self, action: str, locator: Locator, *extra: str) -> None:
        """Append an interaction to :attr:`events`, for tests to assert on."""
        self.events.append((action, str(locator), *extra))

    # ------------------------------------------------------------------- primitivas ---

    def _start(self) -> None:
        self.start_count += 1

    def _stop(self) -> None:
        self.stop_count += 1

    def _find(self, locator: Locator) -> Element:
        return FakeElement(self, locator)

    def _find_all(self, locator: Locator) -> Sequence[Element]:
        nodes = self.nodes.get(locator, [])
        return [FakeElement(self, locator, index) for index in range(len(nodes))]

    def _screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake-screenshot")
        return path

    def _dump_tree(self) -> str:
        """The scripted application, one line per node, children indented under their parent."""

        def render(nodes: dict[Locator, list[FakeNode]], depth: int) -> list[str]:
            lines: list[str] = []
            for locator, siblings in nodes.items():
                for node in siblings:
                    state = "visible" if node.visible else "oculto"
                    lines.append(f"{'  ' * depth}{locator} [{state}] {node.text!r}")
                    lines.extend(render(node.children, depth + 1))
            return lines

        return "\n".join(render(self.nodes, 0))
