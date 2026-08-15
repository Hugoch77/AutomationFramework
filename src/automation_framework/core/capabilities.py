"""What an engine can and cannot do.

Engines differ in ways that matter to the caller: the desktop engine has no idea what a CSS
selector is, and pywinauto cannot record a Playwright trace. Rather than discovering that
through a confusing runtime failure, every engine declares it up front and the base class
turns a mismatch into a precise error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from automation_framework.core.locator import Strategy


class Feature(StrEnum):
    """Optional abilities beyond locating and interacting with elements."""

    SCREENSHOT = "screenshot"
    """Can capture an image of the application under test."""

    TRACING = "tracing"
    """Can record a replayable trace of the session."""

    VIDEO = "video"
    """Can record a video of the session."""

    MULTIPLE_WINDOWS = "multiple_windows"
    """Can drive more than one top-level window or tab."""

    ATTACH_TO_RUNNING = "attach_to_running"
    """Can connect to an already running instance instead of launching a fresh one."""

    ELEMENT_TREE_DUMP = "element_tree_dump"
    """Can dump the element hierarchy, the desktop equivalent of saving the DOM."""


@dataclass(frozen=True, slots=True)
class Capabilities:
    """The declared abilities of one engine.

    Build these with :meth:`of`, which accepts any iterable and freezes it for you.
    """

    name: str
    strategies: frozenset[Strategy]
    features: frozenset[Feature] = field(default_factory=frozenset)

    @classmethod
    def of(
        cls,
        name: str,
        *,
        strategies: Iterable[Strategy],
        features: Iterable[Feature] = (),
    ) -> Capabilities:
        """Build capabilities from any iterables."""
        return cls(name=name, strategies=frozenset(strategies), features=frozenset(features))

    def supports(self, strategy: Strategy) -> bool:
        """Whether this engine can resolve locators using ``strategy``."""
        return strategy in self.strategies

    def has(self, feature: Feature) -> bool:
        """Whether this engine provides ``feature``."""
        return feature in self.features
