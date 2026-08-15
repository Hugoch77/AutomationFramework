"""Tests for the engine registry.

The registry is process-global state, so every test here restores it afterwards. That is
exactly the discipline the framework's own fixtures will need later.
"""

import pytest

from automation_framework.core.exceptions import (
    EngineAlreadyRegisteredError,
    EngineError,
    EngineNotRegisteredError,
)
from automation_framework.core.registry import (
    available_engines,
    clear_registry,
    create_engine,
    is_registered,
    register_engine,
    unregister_engine,
)
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Give each test an empty registry and hand the real one back afterwards."""
    from automation_framework.core import registry

    saved = dict(registry._REGISTRY)
    clear_registry()
    yield
    clear_registry()
    for name, factory in saved.items():
        register_engine(name, factory)


class TestRegistration:
    def test_a_registered_engine_is_reported_as_available(self):
        register_engine("fake", FakeEngine)

        assert is_registered("fake") is True
        assert available_engines() == ("fake",)

    def test_an_unregistered_name_is_not(self):
        assert is_registered("fake") is False

    def test_available_engines_comes_back_sorted(self):
        register_engine("web", FakeEngine)
        register_engine("desktop", FakeEngine)

        assert available_engines() == ("desktop", "web")

    def test_unregister_removes_it(self):
        register_engine("fake", FakeEngine)

        unregister_engine("fake")

        assert is_registered("fake") is False

    def test_unregistering_something_absent_is_harmless(self):
        unregister_engine("nunca-existió")

    def test_clear_empties_everything(self):
        register_engine("fake", FakeEngine)

        clear_registry()

        assert available_engines() == ()


class TestNameNormalisation:
    """Nobody should debug a failure caused by a capital letter."""

    @pytest.mark.parametrize("lookup", ["fake", "FAKE", "Fake", "  fake  "])
    def test_lookup_ignores_case_and_padding(self, lookup):
        register_engine("fake", FakeEngine)

        assert is_registered(lookup) is True
        assert isinstance(create_engine(lookup), FakeEngine)

    def test_registration_is_normalised_too(self):
        register_engine("  WEB  ", FakeEngine)

        assert available_engines() == ("web",)

    def test_an_empty_name_is_rejected(self):
        with pytest.raises(ValueError, match="no puede estar vacío"):
            register_engine("   ", FakeEngine)


class TestCollisions:
    def test_registering_a_taken_name_is_refused(self):
        """Silent shadowing would make two engines fight over one name invisibly."""
        register_engine("fake", FakeEngine)

        with pytest.raises(EngineAlreadyRegisteredError, match="replace=True"):
            register_engine("fake", FakeEngine)

    def test_replace_makes_the_override_explicit(self):
        class OtherEngine(FakeEngine):
            pass

        register_engine("fake", FakeEngine)
        register_engine("fake", OtherEngine, replace=True)

        assert isinstance(create_engine("fake"), OtherEngine)


class TestCreation:
    def test_builds_the_registered_engine(self):
        register_engine("fake", FakeEngine)

        assert isinstance(create_engine("fake"), FakeEngine)

    def test_forwards_options_to_the_factory(self):
        register_engine("fake", FakeEngine)

        engine = create_engine("fake", timeout=2.5, poll_interval=0.5)

        assert engine.timeout == 2.5
        assert engine.poll_interval == 0.5

    def test_accepts_a_function_as_the_factory(self):
        """Factories exist so an engine can be preconfigured without subclassing."""
        register_engine("preconfigurado", lambda **kwargs: FakeEngine(timeout=99, **kwargs))

        assert create_engine("preconfigurado").timeout == 99

    def test_returns_a_new_instance_every_time(self):
        register_engine("fake", FakeEngine)

        assert create_engine("fake") is not create_engine("fake")

    def test_the_engine_comes_back_stopped(self):
        register_engine("fake", FakeEngine)

        assert create_engine("fake").is_started is False


class TestCreationFailures:
    def test_an_unknown_name_says_what_is_available(self):
        register_engine("web", FakeEngine)

        with pytest.raises(EngineNotRegisteredError) as excinfo:
            create_engine("mobile")

        assert excinfo.value.available == ("web",)
        assert "'web'" in str(excinfo.value)

    def test_the_error_hints_at_the_two_usual_causes(self):
        with pytest.raises(EngineNotRegisteredError, match="importar"):
            create_engine("web")

    def test_the_keyerror_is_not_chained(self):
        """A raw KeyError in the traceback adds noise and no information."""
        with pytest.raises(EngineNotRegisteredError) as excinfo:
            create_engine("web")

        assert excinfo.value.__cause__ is None

    def test_a_factory_returning_the_wrong_type_is_caught_immediately(self):
        register_engine("roto", lambda **_: "esto no es un engine")

        with pytest.raises(EngineError, match="no es un Engine"):
            create_engine("roto")

    def test_the_wrong_type_error_names_what_came_back(self):
        register_engine("roto", lambda **_: 42)

        with pytest.raises(EngineError, match="int"):
            create_engine("roto")
