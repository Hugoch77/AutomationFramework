"""Tests for the polling primitives.

Every test here uses a fake clock, so the whole file runs in microseconds. If any of these
ever start taking real time, something has started sleeping for real.
"""

import pytest

from automation_framework.core.exceptions import WaitTimeoutError
from automation_framework.core.waits import wait_until, wait_while

pytestmark = pytest.mark.unit


class FakeClock:
    """A clock that only moves when someone sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


def waiter(clock, condition, **kwargs):
    """Call wait_until with the fake clock wired in."""
    defaults = {"description": "la condición", "clock": clock.time, "sleep": clock.sleep}
    return wait_until(condition, **(defaults | kwargs))


class TestSuccess:
    def test_returns_the_first_truthy_value(self, clock):
        assert waiter(clock, lambda: "listo") == "listo"

    def test_does_not_sleep_when_the_condition_is_already_true(self, clock):
        waiter(clock, lambda: True)

        assert clock.slept == []

    def test_polls_until_the_condition_flips(self, clock):
        calls = {"n": 0}

        def condition():
            calls["n"] += 1
            return calls["n"] >= 3

        assert waiter(clock, condition) is True
        assert calls["n"] == 3
        assert clock.slept == [0.1, 0.1]

    def test_hands_back_the_value_so_it_can_double_as_a_getter(self, clock):
        rows = []

        def condition():
            rows.append("fila")
            return rows or None

        assert waiter(clock, condition) == ["fila"]

    def test_evaluates_once_even_with_a_zero_timeout(self, clock):
        """An element that is already there must not cost a single extra poll."""
        calls = {"n": 0}

        def condition():
            calls["n"] += 1
            return True

        assert waiter(clock, condition, timeout=0) is True
        assert calls["n"] == 1


class TestTimeout:
    def test_raises_when_the_condition_never_becomes_true(self, clock):
        with pytest.raises(WaitTimeoutError) as excinfo:
            waiter(clock, lambda: False, timeout=1.0)

        assert excinfo.value.timeout == 1.0
        assert excinfo.value.description == "la condición"

    def test_message_carries_the_description(self, clock):
        with pytest.raises(WaitTimeoutError, match="que cargue la tabla"):
            waiter(clock, lambda: False, timeout=0.5, description="que cargue la tabla")

    def test_zero_timeout_still_evaluates_once_before_failing(self, clock):
        calls = {"n": 0}

        def condition():
            calls["n"] += 1
            return False

        with pytest.raises(WaitTimeoutError):
            waiter(clock, condition, timeout=0)

        assert calls["n"] == 1
        assert clock.slept == []

    def test_never_sleeps_past_the_deadline(self, clock):
        """The last nap must be trimmed, or a 1.05s budget would take 1.1s."""
        with pytest.raises(WaitTimeoutError):
            waiter(clock, lambda: False, timeout=0.25, poll_interval=0.1)

        assert clock.slept == [0.1, 0.1, pytest.approx(0.05)]
        assert clock.now == pytest.approx(0.25)

    def test_falsy_values_do_not_end_the_wait(self, clock):
        """Empty collections mean "not ready yet", which is what callers expect."""
        with pytest.raises(WaitTimeoutError):
            waiter(clock, list, timeout=0.2)


class TestIgnoredExceptions:
    def test_treats_listed_exceptions_as_not_ready(self, clock):
        calls = {"n": 0}

        def condition():
            calls["n"] += 1
            if calls["n"] < 3:
                raise LookupError("la UI aún se está construyendo")
            return "listo"

        assert waiter(clock, condition, ignored_exceptions=(LookupError,)) == "listo"

    def test_lets_unlisted_exceptions_through(self, clock):
        def condition():
            raise RuntimeError("esto es un bug, no una espera")

        with pytest.raises(RuntimeError, match="esto es un bug"):
            waiter(clock, condition, ignored_exceptions=(LookupError,))

    def test_attaches_the_last_ignored_error_as_the_cause(self, clock):
        """Otherwise the real problem is invisible behind a generic timeout."""

        def condition():
            raise LookupError("no existe el control")

        with pytest.raises(WaitTimeoutError) as excinfo:
            waiter(clock, condition, timeout=0.2, ignored_exceptions=(LookupError,))

        assert isinstance(excinfo.value.__cause__, LookupError)
        assert "no existe el control" in str(excinfo.value.__cause__)

    def test_has_no_cause_when_nothing_was_swallowed(self, clock):
        with pytest.raises(WaitTimeoutError) as excinfo:
            waiter(clock, lambda: False, timeout=0.2)

        assert excinfo.value.__cause__ is None


class TestValidation:
    def test_rejects_a_negative_timeout(self, clock):
        with pytest.raises(ValueError, match="no puede ser negativo"):
            waiter(clock, lambda: True, timeout=-1)

    @pytest.mark.parametrize("interval", [0, -0.5])
    def test_rejects_a_non_positive_poll_interval(self, clock, interval):
        with pytest.raises(ValueError, match="debe ser positivo"):
            waiter(clock, lambda: True, poll_interval=interval)


class TestWaitWhile:
    def test_returns_once_the_condition_goes_away(self, clock):
        calls = {"n": 0}

        def spinner_visible():
            calls["n"] += 1
            return calls["n"] < 3

        wait_while(
            spinner_visible,
            description="que desaparezca el spinner",
            clock=clock.time,
            sleep=clock.sleep,
        )

        assert calls["n"] == 3

    def test_times_out_when_it_never_goes_away(self, clock):
        with pytest.raises(WaitTimeoutError, match="que desaparezca el spinner"):
            wait_while(
                lambda: True,
                description="que desaparezca el spinner",
                timeout=0.2,
                clock=clock.time,
                sleep=clock.sleep,
            )

    def test_returns_immediately_when_already_gone(self, clock):
        wait_while(
            lambda: False,
            description="que desaparezca el spinner",
            clock=clock.time,
            sleep=clock.sleep,
        )

        assert clock.slept == []
