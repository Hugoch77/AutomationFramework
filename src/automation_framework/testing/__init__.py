"""In-memory test doubles for the framework's own test suite.

Shipped inside the package rather than under ``tests/`` so that engine authors can reuse it:
a new engine's unit tests can compare their behaviour against :class:`FakeEngine`, which is the
reference implementation of the contracts.
"""

from automation_framework.testing.fake import FakeElement, FakeEngine, FakeNode

__all__ = ["FakeElement", "FakeEngine", "FakeNode"]
