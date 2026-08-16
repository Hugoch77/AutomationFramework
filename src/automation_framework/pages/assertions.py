"""Assertions that wait, and that say what went wrong.

Two things separate these from a bare ``assert element.text() == "Products"``:

* **They retry.** A UI is asynchronous; reading once and comparing is how a suite acquires
  flaky tests. Every assertion here polls until the expectation holds or the budget runs out.
* **They report.** ``assert a == b`` on a missing element raises ``ElementNotFoundError`` from
  inside the read, and the failure says nothing about what the test expected. These name the
  element, the expectation and what was actually there when the wait gave up.

They raise ``AssertionError`` on purpose, not a framework exception: pytest reports it as a
*failure* (the app did not do what the test said) rather than an *error* (the test itself broke),
and that distinction is the whole point of a test report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn

from automation_framework.core.element import ElementState
from automation_framework.core.exceptions import AutomationError
from automation_framework.core.waits import wait_until

if TYPE_CHECKING:
    from collections.abc import Callable

    from automation_framework.core.element import Element
    from automation_framework.core.engine import Engine
    from automation_framework.core.locator import Locator

__all__ = [
    "expect_count",
    "expect_hidden",
    "expect_text",
    "expect_text_containing",
    "expect_value",
    "expect_visible",
]


class _Attempt:
    """What the last poll saw, so the failure message can report it."""

    def __init__(self) -> None:
        self.value: Any = None
        self.seen = False
        self.error: Exception | None = None

    @property
    def detail(self) -> str:
        """How to describe the last observation."""
        if self.seen:
            return f"se encontró {self.value!r}"
        if self.error is not None:
            return f"la lectura falló con: {self.error}"
        return "nunca se pudo leer"  # pragma: no cover - wait_until siempre sondea una vez


def _fail(message: str, custom: str | None) -> NoReturn:
    """Raise the failure, letting the caller prepend their own context.

    The custom message is added to the generated one rather than replacing it: a test author
    explaining *why* they expected something should not have to also restate what was found.
    """
    raise AssertionError(f"{custom}\n{message}" if custom else message)


def _failure_after_polling(
    read: Callable[[], Any],
    matches: Callable[[Any], bool],
    *,
    description: str,
    timeout: float,
    poll_interval: float,
) -> _Attempt | None:
    """Poll ``read`` until ``matches`` accepts what it returns.

    Returns ``None`` when the expectation held, or the last :class:`_Attempt` when it never
    did — so the caller has something concrete to put in the failure message.

    Read errors are swallowed while the budget lasts, since an element that is not there *yet*
    is the normal case mid-transition. The last one is kept, because "it never showed up" and
    "reading it kept blowing up" call for different fixes.
    """
    attempt = _Attempt()

    def condition() -> bool:
        try:
            value = read()
        except AutomationError as error:
            attempt.error = error
            attempt.seen = False
            return False
        attempt.value = value
        attempt.seen = True
        return matches(value)

    try:
        wait_until(
            condition,
            description=description,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    except AutomationError:
        return attempt
    return None


def _budget(element: Element, timeout: float | None) -> tuple[float, float]:
    """The wait budget for an assertion: the element's own, unless overridden."""
    return (element.timeout if timeout is None else timeout, element.poll_interval)


# ------------------------------------------------------------------------- presencia ---


def expect_visible(
    element: Element, *, timeout: float | None = None, message: str | None = None
) -> None:
    """Assert that ``element`` is displayed, waiting for it to become so."""
    budget, _ = _budget(element, timeout)
    try:
        element.wait_for(ElementState.VISIBLE, timeout=budget)
    except AutomationError:
        _fail(
            f"Se esperaba que {element.locator} estuviera visible, "
            f"pero no lo estaba tras {budget:g}s.",
            message,
        )


def expect_hidden(
    element: Element, *, timeout: float | None = None, message: str | None = None
) -> None:
    """Assert that ``element`` is not displayed, waiting for it to go away.

    Satisfied both by an element that is absent and by one that is present but not shown:
    from the user's side of the screen those are the same thing.
    """
    budget, _ = _budget(element, timeout)
    try:
        element.wait_for(ElementState.HIDDEN, timeout=budget)
    except AutomationError:
        _fail(
            f"Se esperaba que {element.locator} no estuviera visible, "
            f"pero seguía en pantalla tras {budget:g}s.",
            message,
        )


# ---------------------------------------------------------------------------- textos ---


def expect_text(
    element: Element,
    expected: str,
    *,
    timeout: float | None = None,
    message: str | None = None,
) -> None:
    """Assert that ``element``'s text equals ``expected``, waiting for it to settle.

    Surrounding whitespace is ignored: markup indentation is a property of the HTML, not of
    what the user reads, and a test that fails over a newline teaches people to distrust it.
    """
    budget, poll = _budget(element, timeout)
    target = expected.strip()
    failure = _failure_after_polling(
        lambda: element.text(timeout=0).strip(),
        lambda value: value == target,
        description=f"que el texto de {element.locator} sea {target!r}",
        timeout=budget,
        poll_interval=poll,
    )
    if failure is not None:
        _fail(
            f"Se esperaba que {element.locator} mostrara {target!r}, "
            f"pero {failure.detail} tras {budget:g}s.",
            message,
        )


def expect_text_containing(
    element: Element,
    fragment: str,
    *,
    timeout: float | None = None,
    message: str | None = None,
) -> None:
    """Assert that ``element``'s text contains ``fragment``.

    For copy a test should not pin down word for word — errors and notifications get rephrased,
    and asserting the whole sentence makes the suite fail on an edit that broke nothing.
    """
    budget, poll = _budget(element, timeout)
    failure = _failure_after_polling(
        lambda: element.text(timeout=0),
        lambda value: fragment in value,
        description=f"que el texto de {element.locator} contenga {fragment!r}",
        timeout=budget,
        poll_interval=poll,
    )
    if failure is not None:
        _fail(
            f"Se esperaba que {element.locator} contuviera {fragment!r}, "
            f"pero {failure.detail} tras {budget:g}s.",
            message,
        )


def expect_value(
    element: Element,
    expected: str,
    *,
    timeout: float | None = None,
    message: str | None = None,
) -> None:
    """Assert that a field's editable value equals ``expected``.

    Uses :meth:`~automation_framework.core.element.Element.value`, not ``attribute("value")``:
    the declared attribute does not change when the user types.
    """
    budget, poll = _budget(element, timeout)
    failure = _failure_after_polling(
        lambda: element.value(timeout=0),
        lambda value: value == expected,
        description=f"que el valor de {element.locator} sea {expected!r}",
        timeout=budget,
        poll_interval=poll,
    )
    if failure is not None:
        _fail(
            f"Se esperaba que {element.locator} tuviera el valor {expected!r}, "
            f"pero {failure.detail} tras {budget:g}s.",
            message,
        )


# -------------------------------------------------------------------------- cantidad ---


def expect_count(
    engine: Engine,
    locator: Locator,
    expected: int,
    *,
    timeout: float | None = None,
    message: str | None = None,
) -> None:
    """Assert how many elements match ``locator``, waiting for the count to settle.

    Takes the engine and the locator rather than a resolved list, because a list is a snapshot:
    a suite asserting on one it resolved earlier cannot wait for a table that is still filling
    in, which is precisely when the count is worth asserting.
    """
    budget = engine.timeout if timeout is None else timeout
    failure = _failure_after_polling(
        lambda: len(engine.find_all(locator)),
        lambda value: value == expected,
        description=f"que haya {expected} elementos {locator}",
        timeout=budget,
        poll_interval=engine.poll_interval,
    )
    if failure is not None:
        _fail(
            f"Se esperaban {expected} elementos {locator}, pero {failure.detail} tras {budget:g}s.",
            message,
        )
