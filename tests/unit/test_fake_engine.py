"""Tests for the in-memory test double.

FakeEngine is the reference implementation of the core contracts, so its own behaviour has to
be trustworthy: every other test in the suite believes what it says.
"""

import pytest

from automation_framework.core.capabilities import Feature
from automation_framework.core.exceptions import ElementError
from automation_framework.core.locator import Locator, Strategy
from automation_framework.testing import FakeElement, FakeEngine, FakeNode

pytestmark = pytest.mark.unit

BUTTON = Locator.test_id("submit")


@pytest.fixture
def engine():
    with FakeEngine(timeout=0.05, poll_interval=0.001) as engine:
        yield engine


class TestCapabilities:
    def test_accepts_every_strategy(self):
        """Deliberate: this double exists to exercise the rest of the contract, not limits."""
        engine = FakeEngine()

        assert all(engine.supports(strategy) for strategy in Strategy)

    def test_declares_the_features_it_implements(self):
        engine = FakeEngine()

        assert engine.has_feature(Feature.SCREENSHOT) is True
        assert engine.has_feature(Feature.TRACING) is False

    def test_is_named_fake(self):
        assert FakeEngine().name == "fake"


class TestScenarioSetup:
    def test_add_returns_the_node_so_it_can_be_mutated_later(self, engine):
        node = engine.add(BUTTON, text="Enviar")

        node.text = "Guardar"

        assert engine.find(BUTTON).text() == "Guardar"

    def test_add_registers_several_nodes_under_one_locator(self, engine):
        engine.add(BUTTON, text="uno")
        engine.add(BUTTON, text="dos")

        assert len(engine.find_all(BUTTON)) == 2

    def test_attributes_are_copied_not_shared(self, engine):
        shared = {"href": "/inicio"}
        engine.add(BUTTON, attributes=shared)

        shared["href"] = "/otro"

        assert engine.find(BUTTON).attribute("href") == "/inicio"

    def test_remove_takes_the_element_out_of_the_tree(self, engine):
        engine.add(BUTTON)
        element = engine.find(BUTTON)

        engine.remove(BUTTON)

        assert element.exists() is False

    def test_removing_something_absent_is_harmless(self, engine):
        engine.remove(BUTTON)

    def test_find_all_is_empty_after_removal(self, engine):
        engine.add(BUTTON)
        engine.remove(BUTTON)

        assert engine.find_all(BUTTON) == []


class TestScriptedAppearance:
    """`appear_after` is how waiting gets tested without real time passing."""

    def test_a_node_is_invisible_until_its_turn(self):
        node = FakeNode(appear_after=2)

        assert node.exists() is False
        assert node.exists() is False
        assert node.exists() is True

    def test_it_stays_present_afterwards(self):
        node = FakeNode(appear_after=1)
        node.exists()

        assert node.exists() is True
        assert node.exists() is True

    def test_lookups_are_counted(self, engine):
        node = engine.add(BUTTON)
        engine.find(BUTTON).exists()
        engine.find(BUTTON).exists()

        assert node.lookups == 2

    def test_zero_means_immediately_there(self):
        assert FakeNode().exists() is True


class TestInteractionRecording:
    def test_clicks_are_recorded_in_order(self, engine):
        engine.add(BUTTON)

        engine.find(BUTTON).click()
        engine.find(BUTTON).click()

        assert engine.events == [("click", str(BUTTON))] * 2

    def test_fill_stores_the_value_on_the_node(self, engine):
        engine.add(BUTTON)

        engine.find(BUTTON).fill("notepad")

        assert engine.find(BUTTON).value() == "notepad"

    def test_the_typed_value_is_not_the_declared_attribute(self, engine):
        """The distinction that Fase 2 uncovered against a real browser."""
        engine.add(BUTTON, attributes={"value": "declarado"})

        engine.find(BUTTON).fill("escrito")

        assert engine.find(BUTTON).value() == "escrito"
        assert engine.find(BUTTON).attribute("value") == "declarado"

    def test_reading_the_value_of_a_non_field_is_refused(self, engine):
        engine.add(BUTTON, editable=False)

        with pytest.raises(ElementError, match="no tiene un valor editable"):
            engine.find(BUTTON).value()

    def test_the_value_of_a_missing_element_is_empty(self, engine):
        assert FakeElement(engine, BUTTON, index=5)._value() == ""

    def test_fill_tolerates_a_node_that_vanished(self, engine):
        """Defensive branch: the tree can change between the wait and the action."""
        engine.add(BUTTON)
        element = engine.find(BUTTON)
        engine.remove(BUTTON)

        element._fill("notepad")

        assert engine.events == [("fill", str(BUTTON), "notepad")]


class TestLifecycleCounters:
    def test_counts_starts_and_stops(self):
        engine = FakeEngine()

        with engine:
            pass

        assert (engine.start_count, engine.stop_count) == (1, 1)


class TestScreenshot:
    def test_writes_a_file(self, engine, tmp_path):
        destination = engine.screenshot(tmp_path / "captura.png")

        assert destination.read_bytes() == b"fake-screenshot"

    def test_creates_missing_directories(self, engine, tmp_path):
        destination = engine.screenshot(tmp_path / "a" / "b" / "captura.png")

        assert destination.exists()


class TestElementIndexing:
    def test_each_handle_targets_its_own_node(self, engine):
        engine.add(BUTTON, text="uno")
        engine.add(BUTTON, text="dos")

        first, second = engine.find_all(BUTTON)

        assert (first.text(), second.text()) == ("uno", "dos")

    def test_an_index_past_the_end_behaves_as_missing(self, engine):
        engine.add(BUTTON)

        assert FakeElement(engine, BUTTON, index=5).exists() is False

    def test_text_of_a_missing_element_is_empty(self, engine):
        assert FakeElement(engine, BUTTON, index=5)._text() == ""

    def test_attribute_of_a_missing_element_is_none(self, engine):
        assert FakeElement(engine, BUTTON, index=5)._attribute("href") is None
