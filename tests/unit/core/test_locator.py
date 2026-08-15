"""Tests for the engine-agnostic locator descriptor."""

import pytest

from automation_framework.core.locator import Locator, Strategy

pytestmark = pytest.mark.unit


class TestConstruction:
    def test_requires_a_non_empty_value(self):
        with pytest.raises(ValueError, match="no puede estar vacío"):
            Locator(Strategy.CSS, "")

    def test_shortcuts_set_the_matching_strategy(self):
        assert Locator.test_id("x").strategy is Strategy.TEST_ID
        assert Locator.css("x").strategy is Strategy.CSS
        assert Locator.xpath("x").strategy is Strategy.XPATH
        assert Locator.automation_id("x").strategy is Strategy.AUTOMATION_ID
        assert Locator.control_type("x").strategy is Strategy.CONTROL_TYPE
        assert Locator.class_name("x").strategy is Strategy.CLASS_NAME
        assert Locator.text("x").strategy is Strategy.TEXT
        assert Locator.name("x").strategy is Strategy.NAME

    def test_role_shortcut_carries_the_accessible_name_as_an_option(self):
        locator = Locator.role("button", name="Buscar")

        assert locator.strategy is Strategy.ROLE
        assert locator.value == "button"
        assert locator.options == {"name": "Buscar"}

    def test_role_without_name_has_no_options(self):
        assert Locator.role("button").options == {}


class TestImmutability:
    """Locators are declared as module-level constants, so they must be safe to share."""

    def test_is_frozen(self):
        locator = Locator.test_id("search")

        with pytest.raises(AttributeError):
            locator.value = "other"  # type: ignore[misc]

    def test_is_hashable_and_usable_as_a_dict_key(self):
        locator = Locator.test_id("search")

        assert {locator: "ok"}[Locator.test_id("search")] == "ok"

    def test_options_do_not_affect_identity(self):
        """Two locators pointing at the same element are the same element.

        Options are engine hints, not part of what is being identified. If they took part in
        equality, a hashable locator would stop being usable as a key the moment an engine
        enriched it.
        """
        plain = Locator(Strategy.ROLE, "button")
        hinted = Locator(Strategy.ROLE, "button", options={"name": "Buscar"})

        assert plain == hinted
        assert hash(plain) == hash(hinted)

    def test_description_is_part_of_identity(self):
        assert Locator.test_id("x", description="uno") != Locator.test_id("x", description="dos")


class TestWithOptions:
    def test_returns_a_new_locator_and_leaves_the_original_untouched(self):
        original = Locator.role("button")

        derived = original.with_options(name="Buscar")

        assert derived is not original
        assert original.options == {}
        assert derived.options == {"name": "Buscar"}

    def test_merges_instead_of_replacing(self):
        locator = Locator(Strategy.ROLE, "button", options={"exact": True})

        derived = locator.with_options(name="Buscar")

        assert derived.options == {"exact": True, "name": "Buscar"}

    def test_later_options_win(self):
        locator = Locator(Strategy.ROLE, "button", options={"name": "viejo"})

        assert locator.with_options(name="nuevo").options == {"name": "nuevo"}

    def test_preserves_strategy_value_and_description(self):
        locator = Locator.automation_id("SearchBox", description="caja de búsqueda")

        derived = locator.with_options(timeout=5)

        assert derived.strategy is locator.strategy
        assert derived.value == locator.value
        assert derived.description == locator.description


class TestRendering:
    """The string form ends up in every error message, so it is worth pinning down."""

    def test_uses_the_description_when_present(self):
        locator = Locator.automation_id("SearchBox", description="caja de búsqueda")

        assert str(locator) == "'caja de búsqueda' (automation_id='SearchBox')"

    def test_falls_back_to_the_value(self):
        assert str(Locator.css("button.primary")) == "'button.primary' (css='button.primary')"

    def test_strategy_repr_is_readable(self):
        assert repr(Strategy.AUTOMATION_ID) == "Strategy.AUTOMATION_ID"

    def test_strategy_is_a_string_enum(self):
        assert Strategy.CSS == "css"
