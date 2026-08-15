"""Explicit, condition-based waiting.

This is the only place in the framework allowed to sleep. Everything else waits by asking
*"is it ready yet?"* through :func:`wait_until`, never by guessing a duration.

The clock and the sleep function are injectable. That is not gold-plating: it is what lets the
unit tests cover timeout and retry behaviour in microseconds instead of making the suite sit
there for ten real seconds.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from automation_framework.core.exceptions import WaitTimeoutError

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_TIMEOUT = 10.0
"""Seconds a condition is given before giving up."""

DEFAULT_POLL_INTERVAL = 0.1
"""Seconds between attempts. Small enough to feel instant, large enough not to spin the CPU."""


def wait_until[T](
    condition: Callable[[], T | None],
    *,
    description: str,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    ignored_exceptions: tuple[type[Exception], ...] = (),
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Poll ``condition`` until it returns something truthy, then return that value.

    Args:
        condition: Called repeatedly. Any truthy return value ends the wait and is handed back,
            so a condition can double as a getter (``lambda: engine.find_all(row) or None``).
        description: What is being waited for, phrased to complete "se agotó la espera para: ...".
            It is the only clue the failure message carries, so make it specific.
        timeout: Total budget in seconds. ``0`` still evaluates the condition exactly once.
        poll_interval: Delay between attempts.
        ignored_exceptions: Exception types to treat as "not ready yet" instead of letting them
            propagate. Useful while a UI is still building itself and lookups legitimately fail.
        clock: Monotonic time source. Injectable for testing.
        sleep: Delay function. Injectable for testing.

    Returns:
        The first truthy value produced by ``condition``.

    Raises:
        WaitTimeoutError: The condition never became truthy within ``timeout``. If an ignored
            exception was seen, it is attached as the cause so the real problem is not lost.
        ValueError: ``timeout`` is negative or ``poll_interval`` is not positive.
    """
    if timeout < 0:
        raise ValueError(f"El timeout no puede ser negativo: {timeout!r}.")
    if poll_interval <= 0:
        raise ValueError(f"El intervalo de sondeo debe ser positivo: {poll_interval!r}.")

    deadline = clock() + timeout
    last_error: Exception | None = None

    # Bucle "do-while": la condición se evalúa siempre al menos una vez, incluso con timeout=0.
    # Un elemento que ya está listo no debe costar ni un sondeo extra.
    while True:
        try:
            result = condition()
        except ignored_exceptions as error:
            last_error = error
        else:
            if result:
                return result

        remaining = deadline - clock()
        if remaining <= 0:
            raise WaitTimeoutError(description, timeout) from last_error

        sleep(min(poll_interval, remaining))


def wait_while[T](
    condition: Callable[[], T],
    *,
    description: str,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    ignored_exceptions: tuple[type[Exception], ...] = (),
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Wait until ``condition`` stops being truthy.

    The mirror image of :func:`wait_until`, for disappearances: a spinner going away, a modal
    closing, an element being removed.
    """
    wait_until(
        lambda: not condition(),
        description=description,
        timeout=timeout,
        poll_interval=poll_interval,
        ignored_exceptions=ignored_exceptions,
        clock=clock,
        sleep=sleep,
    )
