"""Tests for the element contract.

Driven through FakeEngine, which is the reference implementation of the primitives.
What is under test here is the shared behaviour every engine inherits: laziness, the
auto-waiting policy, and how failures are reported.
"""

import pytest

from automation_framework.core.element import ElementState
from automation_framework.core.exceptions import (
    ElementError,
    ElementNotFoundError,
    WaitTimeoutError,
)
from automation_framework.core.locator import Locator
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

BUTTON = Locator.test_id("submit", description="botón de enviar")
MISSING = Locator.test_id("nope", description="algo que no existe")
SELECTOR = Locator.test_id("orden", description="desplegable de orden")


@pytest.fixture
def engine():
    # Timeout diminuto: si un test espera de verdad, debe fallar rápido en vez de
    # frenar la suite. Aquí nada tarda, todo está en un diccionario.
    with FakeEngine(timeout=0.05, poll_interval=0.001) as engine:
        yield engine


class TestLaziness:
    def test_find_does_not_touch_the_application(self, engine):
        """The whole point of lazy handles: locators can be module-level constants."""
        element = engine.find(MISSING)

        assert element is not None
        assert engine.events == []

    def test_the_handle_exposes_its_locator(self, engine):
        assert engine.find(BUTTON).locator is BUTTON

    def test_repr_identifies_the_element(self, engine):
        assert "botón de enviar" in repr(engine.find(BUTTON))

    def test_a_handle_created_before_the_element_exists_still_works(self, engine):
        element = engine.find(BUTTON)
        engine.add(BUTTON)

        element.click()

        assert engine.events == [("click", str(BUTTON))]


class TestQueries:
    """Queries answer now. Asking "is it there?" must not block for ten seconds."""

    def test_exists_is_false_for_an_unknown_element(self, engine):
        assert engine.find(MISSING).exists() is False

    def test_exists_is_true_once_added(self, engine):
        engine.add(BUTTON)

        assert engine.find(BUTTON).exists() is True

    def test_is_visible_is_false_for_a_hidden_element(self, engine):
        engine.add(BUTTON, visible=False)

        assert engine.find(BUTTON).is_visible() is False

    def test_is_visible_is_false_for_a_missing_element(self, engine):
        assert engine.find(MISSING).is_visible() is False

    def test_queries_do_not_wait(self, engine):
        """appear_after=5 means it would need six polls; a query must give up after one."""
        engine.add(BUTTON, appear_after=5)

        assert engine.find(BUTTON).exists() is False


class TestActions:
    def test_click_waits_for_visibility_then_acts(self, engine):
        engine.add(BUTTON, appear_after=2)

        engine.find(BUTTON).click()

        assert engine.events == [("click", str(BUTTON))]

    def test_fill_replaces_the_value(self, engine):
        engine.add(BUTTON)

        engine.find(BUTTON).fill("notepad")

        assert engine.events == [("fill", str(BUTTON), "notepad")]

    def test_text_reads_the_content(self, engine):
        engine.add(BUTTON, text="Enviar")

        assert engine.find(BUTTON).text() == "Enviar"

    def test_attribute_reads_a_named_value(self, engine):
        engine.add(BUTTON, attributes={"href": "/inicio"})

        assert engine.find(BUTTON).attribute("href") == "/inicio"

    def test_attribute_is_none_when_absent(self, engine):
        engine.add(BUTTON)

        assert engine.find(BUTTON).attribute("href") is None

    def test_actions_wait_for_a_late_element(self, engine):
        engine.add(BUTTON, text="Enviar", appear_after=3)

        assert engine.find(BUTTON).text() == "Enviar"


class TestSelect:
    """Choosing in a dropdown is its own operation, not a variant of filling.

    Typing into a `<select>` does nothing, so without this primitive a suite would have to
    reach past the contract into the automation library.
    """

    def test_select_chooses_an_option(self, engine):
        engine.add(SELECTOR, options=("lohi", "hilo"))

        engine.find(SELECTOR).select("lohi")

        assert engine.events == [("select", str(SELECTOR), "lohi")]

    def test_select_records_the_chosen_value(self, engine):
        engine.add(SELECTOR, options=("lohi", "hilo"))

        engine.find(SELECTOR).select("hilo")

        assert engine.find(SELECTOR).value() == "hilo"

    def test_select_waits_for_a_late_element(self, engine):
        engine.add(SELECTOR, options=("lohi",), appear_after=2)

        engine.find(SELECTOR).select("lohi")

        assert engine.find(SELECTOR).value() == "lohi"

    def test_an_option_that_does_not_exist_fails(self, engine):
        """Elegir algo que no está es un error del test, y debe decirlo."""
        engine.add(SELECTOR, options=("lohi", "hilo"))

        with pytest.raises(ElementError, match="hilo"):
            engine.find(SELECTOR).select("por-fecha")

    def test_selecting_on_something_that_is_not_a_dropdown_fails(self, engine):
        """El doble no puede ser más permisivo que el engine real.

        Playwright rechaza `select_option` sobre lo que no es un `<select>`; si aquí pasara
        en silencio, un test unitario quedaría verde y reventaría contra el navegador.
        """
        engine.add(BUTTON, text="Enviar")

        with pytest.raises(ElementError, match="no es una lista de opciones"):
            engine.find(BUTTON).select("lohi")

    def test_a_rejected_selection_never_reaches_the_application(self, engine):
        engine.add(BUTTON, text="Enviar")

        with pytest.raises(ElementError):
            engine.find(BUTTON).select("lohi")

        assert engine.events == []

    def test_select_on_a_missing_element_reports_the_element(self, engine):
        with pytest.raises(ElementNotFoundError):
            engine.find(MISSING).select("lohi")


class TestActionFailures:
    """A failed action must say which element, not just "timeout"."""

    def test_click_on_a_missing_element_raises_element_not_found(self, engine):
        with pytest.raises(ElementNotFoundError) as excinfo:
            engine.find(MISSING).click(timeout=0)

        assert excinfo.value.locator is MISSING
        assert "algo que no existe" in str(excinfo.value)

    def test_click_on_a_hidden_element_raises_element_not_found(self, engine):
        engine.add(BUTTON, visible=False)

        with pytest.raises(ElementNotFoundError):
            engine.find(BUTTON).click(timeout=0)

    def test_the_underlying_timeout_is_kept_as_the_cause(self, engine):
        with pytest.raises(ElementNotFoundError) as excinfo:
            engine.find(MISSING).text(timeout=0)

        assert isinstance(excinfo.value.__cause__, WaitTimeoutError)

    def test_a_failed_action_never_reaches_the_application(self, engine):
        with pytest.raises(ElementNotFoundError):
            engine.find(MISSING).click(timeout=0)

        assert engine.events == []


class TestWaitFor:
    def test_returns_self_so_it_chains(self, engine):
        engine.add(BUTTON)
        element = engine.find(BUTTON)

        assert element.wait_for() is element

    def test_defaults_to_waiting_for_visibility(self, engine):
        engine.add(BUTTON, visible=False)

        with pytest.raises(ElementNotFoundError):
            engine.find(BUTTON).wait_for(timeout=0)

    def test_present_ignores_visibility(self, engine):
        engine.add(BUTTON, visible=False)

        engine.find(BUTTON).wait_for(ElementState.PRESENT, timeout=0)

    def test_hidden_is_satisfied_by_an_invisible_element(self, engine):
        engine.add(BUTTON, visible=False)

        engine.find(BUTTON).wait_for(ElementState.HIDDEN, timeout=0)

    def test_hidden_is_satisfied_by_a_missing_element(self, engine):
        engine.find(MISSING).wait_for(ElementState.HIDDEN, timeout=0)

    def test_absent_is_satisfied_by_a_missing_element(self, engine):
        engine.find(MISSING).wait_for(ElementState.ABSENT, timeout=0)

    def test_absent_fails_while_the_element_is_still_there(self, engine):
        engine.add(BUTTON)

        with pytest.raises(WaitTimeoutError):
            engine.find(BUTTON).wait_for(ElementState.ABSENT, timeout=0)

    def test_disappearance_reports_a_timeout_not_a_missing_element(self, engine):
        """ "No se fue" and "no vino" are different diagnoses and must not be conflated."""
        engine.add(BUTTON)

        with pytest.raises(WaitTimeoutError) as excinfo:
            engine.find(BUTTON).wait_for(ElementState.ABSENT, timeout=0)

        assert not isinstance(excinfo.value, ElementNotFoundError)

    def test_an_explicit_timeout_overrides_the_engine_default(self, engine):
        with pytest.raises(ElementNotFoundError) as excinfo:
            engine.find(MISSING).wait_for(timeout=0.02)

        assert excinfo.value.timeout == 0.02

    def test_falls_back_to_the_engine_timeout(self, engine):
        with pytest.raises(ElementNotFoundError) as excinfo:
            engine.find(MISSING).wait_for()

        assert excinfo.value.timeout == engine.timeout

    def test_the_message_names_the_expected_state(self, engine):
        engine.add(BUTTON)

        with pytest.raises(WaitTimeoutError, match="absent"):
            engine.find(BUTTON).wait_for(ElementState.ABSENT, timeout=0)
