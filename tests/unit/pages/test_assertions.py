"""Tests for the waiting assertions.

Two properties matter here and both are easy to lose:

* they must **wait**, or the suite gets flaky the first time the app is slow;
* they must **explain**, or a red build costs a debugging session instead of a glance.

Driven through `FakeEngine`, so waiting behaviour is covered without real time passing.
"""

import pytest

from automation_framework.core.locator import Locator
from automation_framework.pages import (
    expect_count,
    expect_hidden,
    expect_text,
    expect_text_containing,
    expect_value,
    expect_visible,
)
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

TITULO = Locator.test_id("titulo", description="título de la página")
CAMPO = Locator.test_id("campo", description="campo de usuario")
FILA = Locator.css("li.fila", description="filas de la tabla")
AUSENTE = Locator.test_id("no-existe", description="algo que no está")


@pytest.fixture
def engine():
    with FakeEngine() as instance:
        yield instance


class TestExpectVisible:
    def test_passes_when_the_element_is_shown(self, engine):
        engine.add(TITULO, text="Hola")

        expect_visible(engine.find(TITULO))

    def test_waits_for_an_element_that_arrives_late(self, engine):
        """The whole point: a slow render must not be a failure."""
        engine.add(TITULO, text="Hola", appear_after=3)

        expect_visible(engine.find(TITULO))

    def test_fails_when_the_element_never_shows_up(self, engine):
        with pytest.raises(AssertionError):
            expect_visible(engine.find(AUSENTE), timeout=0)

    def test_fails_when_the_element_is_present_but_not_displayed(self, engine):
        engine.add(TITULO, text="Hola", visible=False)

        with pytest.raises(AssertionError):
            expect_visible(engine.find(TITULO), timeout=0)

    def test_the_failure_names_the_element(self, engine):
        """`assert x.is_visible()` says `assert False`, which helps nobody."""
        with pytest.raises(AssertionError, match="título de la página"):
            expect_visible(engine.find(TITULO), timeout=0)

    def test_it_fails_rather_than_erroring(self, engine):
        """AssertionError means "the app misbehaved"; anything else means "the test broke"."""
        with pytest.raises(AssertionError):
            expect_visible(engine.find(AUSENTE), timeout=0)


class TestExpectHidden:
    def test_passes_when_the_element_is_absent(self, engine):
        expect_hidden(engine.find(AUSENTE))

    def test_passes_when_the_element_is_present_but_not_displayed(self, engine):
        """From the user's side of the screen, invisible and absent are the same thing."""
        engine.add(TITULO, visible=False)

        expect_hidden(engine.find(TITULO))

    def test_fails_when_the_element_is_on_screen(self, engine):
        engine.add(TITULO, text="Hola")

        with pytest.raises(AssertionError, match="seguía en pantalla"):
            expect_hidden(engine.find(TITULO), timeout=0)


class TestExpectText:
    def test_passes_on_an_exact_match(self, engine):
        engine.add(TITULO, text="Products")

        expect_text(engine.find(TITULO), "Products")

    def test_ignores_surrounding_whitespace(self, engine):
        """Markup indentation is not something the user reads."""
        engine.add(TITULO, text="\n  Products\n")

        expect_text(engine.find(TITULO), "Products")

    def test_waits_for_text_that_arrives_late(self, engine):
        engine.add(TITULO, text="Products", appear_after=3)

        expect_text(engine.find(TITULO), "Products")

    def test_fails_on_a_different_text(self, engine):
        engine.add(TITULO, text="Carrito")

        with pytest.raises(AssertionError):
            expect_text(engine.find(TITULO), "Products", timeout=0)

    def test_the_failure_reports_both_sides(self, engine):
        """Knowing only what was expected means going to look up what was there."""
        engine.add(TITULO, text="Carrito")

        with pytest.raises(AssertionError) as excinfo:
            expect_text(engine.find(TITULO), "Products", timeout=0)

        assert "Products" in str(excinfo.value)
        assert "Carrito" in str(excinfo.value)

    def test_the_failure_distinguishes_a_missing_element_from_a_wrong_text(self, engine):
        """Different diagnoses, different fixes: navigation vs. a changed label."""
        with pytest.raises(AssertionError, match="la lectura falló"):
            expect_text(engine.find(AUSENTE), "Products", timeout=0)

    def test_a_custom_message_is_added_to_the_generated_one(self, engine):
        """Explaining *why* should not cost the reader what was actually found."""
        engine.add(TITULO, text="Carrito")

        with pytest.raises(AssertionError) as excinfo:
            expect_text(engine.find(TITULO), "Products", timeout=0, message="tras el login")

        assert "tras el login" in str(excinfo.value)
        assert "Carrito" in str(excinfo.value)


class TestExpectTextContaining:
    def test_passes_when_the_fragment_is_present(self, engine):
        engine.add(TITULO, text="Epic sadface: usuario y contraseña no coinciden")

        expect_text_containing(engine.find(TITULO), "no coinciden")

    def test_fails_when_the_fragment_is_absent(self, engine):
        engine.add(TITULO, text="Todo bien")

        with pytest.raises(AssertionError, match="no coinciden"):
            expect_text_containing(engine.find(TITULO), "no coinciden", timeout=0)


class TestExpectValue:
    def test_reads_what_was_typed_not_the_declared_attribute(self, engine):
        engine.add(CAMPO, attributes={"value": "declarado"}, value="")
        engine.find(CAMPO).fill("tecleado")

        expect_value(engine.find(CAMPO), "tecleado")

    def test_fails_on_a_different_value(self, engine):
        engine.add(CAMPO, value="otra cosa")

        with pytest.raises(AssertionError):
            expect_value(engine.find(CAMPO), "esperado", timeout=0)

    def test_the_failure_reports_what_the_field_held(self, engine):
        engine.add(CAMPO, value="otra cosa")

        with pytest.raises(AssertionError, match="otra cosa"):
            expect_value(engine.find(CAMPO), "esperado", timeout=0)


class _EngineThatFillsUpLate(FakeEngine):
    """Rows appear only after a few lookups, the way a table populates asynchronously."""

    def __init__(self, locator, total, *, after):
        super().__init__()
        self._locator = locator
        self._total = total
        self._after = after
        self._calls = 0

    def _find_all(self, locator):
        self._calls += 1
        if self._calls > self._after and not self.nodes.get(locator):
            for index in range(self._total):
                self.add(locator, text=f"fila {index}")
        return super()._find_all(locator)


class TestExpectCount:
    def test_passes_on_the_expected_number(self, engine):
        for index in range(3):
            engine.add(FILA, text=str(index))

        expect_count(engine, FILA, 3)

    def test_passes_on_zero(self, engine):
        expect_count(engine, FILA, 0)

    def test_waits_for_a_table_that_is_still_filling_in(self):
        """Why it takes the engine and locator instead of a resolved list: a snapshot
        cannot grow, so asserting on one could never wait."""
        with _EngineThatFillsUpLate(FILA, 6, after=2) as engine:
            expect_count(engine, FILA, 6)

    def test_fails_on_the_wrong_number(self, engine):
        engine.add(FILA, text="única")

        with pytest.raises(AssertionError):
            expect_count(engine, FILA, 6, timeout=0)

    def test_the_failure_reports_both_numbers(self, engine):
        engine.add(FILA, text="única")

        with pytest.raises(AssertionError) as excinfo:
            expect_count(engine, FILA, 6, timeout=0)

        assert "6" in str(excinfo.value)
        assert "1" in str(excinfo.value)
