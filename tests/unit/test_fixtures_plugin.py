"""Tests for the pytest plugin's configuration merging.

`apply_overrides` is a plain function precisely so it can be tested here, without spinning up
a browser or a nested pytest session. What it protects against is a silent misconfiguration:
a test that declares `@pytest.mark.af_config(...)` and runs with settings that were never
applied is worse than one that fails, because it passes for the wrong reason.
"""

import pytest

from automation_framework.core.config import Settings
from automation_framework.core.exceptions import ConfigurationError
from automation_framework.fixtures.plugin import apply_overrides

pytestmark = pytest.mark.unit


@pytest.fixture
def base():
    return Settings()


class TestApplyOverrides:
    def test_no_overrides_returns_the_same_object(self, base):
        assert apply_overrides(base, {}) is base

    def test_applies_a_known_setting(self, base):
        assert apply_overrides(base, {"test_id_attribute": "data-test"}).test_id_attribute == (
            "data-test"
        )

    def test_keeps_the_settings_it_was_not_asked_to_change(self, base):
        resolved = apply_overrides(base.model_copy(update={}), {"headless": False})

        assert resolved.headless is False
        assert resolved.browser == base.browser
        assert resolved.timeouts.default == base.timeouts.default

    def test_does_not_mutate_the_original(self, base):
        apply_overrides(base, {"headless": False})

        assert base.headless is True

    def test_nested_settings_survive_the_round_trip(self, base):
        """`model_dump` flattens sub-models to dicts; they have to come back as models."""
        resolved = apply_overrides(base, {"headless": False})

        assert resolved.viewport.as_tuple() == base.viewport.as_tuple()


class TestNestedOverrides:
    """Overriding one budget must not silently discard its siblings.

    A flat merge replaces the whole `timeouts` group, so a test asking for a longer navigation
    budget would also reset `default`, `poll_interval` and `startup` to their factory values —
    including anything the environment had configured. It would still pass, just not with the
    configuration it declared.
    """

    def test_a_nested_override_keeps_its_siblings(self, base):
        resolved = apply_overrides(base, {"timeouts": {"navigation": 60}})

        assert resolved.timeouts.navigation == 60
        assert resolved.timeouts.default == base.timeouts.default
        assert resolved.timeouts.poll_interval == base.timeouts.poll_interval
        assert resolved.timeouts.startup == base.timeouts.startup

    def test_a_nested_override_keeps_the_environment_value_of_its_siblings(self, monkeypatch):
        """The sibling that gets clobbered by a flat merge is the one someone configured."""
        monkeypatch.setenv("AF_TIMEOUTS__DEFAULT", "7")
        configured = Settings()

        resolved = apply_overrides(configured, {"timeouts": {"navigation": 60}})

        assert resolved.timeouts.navigation == 60
        assert resolved.timeouts.default == 7

    def test_two_groups_can_be_overridden_at_once(self, base):
        resolved = apply_overrides(
            base, {"timeouts": {"navigation": 45}, "viewport": {"width": 800}}
        )

        assert resolved.timeouts.navigation == 45
        assert resolved.viewport.width == 800
        assert resolved.viewport.height == base.viewport.height

    def test_a_top_level_value_still_replaces_outright(self, base):
        """Deep merging is for groups; a scalar must not acquire merge semantics."""
        assert apply_overrides(base, {"browser": "firefox"}).browser == "firefox"


class TestUnknownOverrides:
    """A typo must fail, not be ignored.

    `model_copy(update=...)` skips validation entirely, so `extra="forbid"` never sees these.
    """

    def test_an_unknown_setting_is_rejected(self, base):
        with pytest.raises(ConfigurationError, match="headles"):
            apply_overrides(base, {"headles": False})

    def test_the_error_names_the_marker(self, base):
        with pytest.raises(ConfigurationError, match="af_config"):
            apply_overrides(base, {"navegador": "chromium"})

    def test_the_error_lists_the_valid_settings(self, base):
        with pytest.raises(ConfigurationError, match="test_id_attribute"):
            apply_overrides(base, {"test_id_atribute": "data-test"})

    def test_every_unknown_name_is_reported_at_once(self, base):
        """Reporting them one per run would mean one failed run per typo."""
        with pytest.raises(ConfigurationError) as excinfo:
            apply_overrides(base, {"headles": False, "navegador": "firefox"})

        assert "headles" in str(excinfo.value)
        assert "navegador" in str(excinfo.value)


class TestInvalidValues:
    """A known name with an impossible value must fail here, not inside the engine."""

    def test_an_invalid_log_level_is_rejected(self, base):
        with pytest.raises(ConfigurationError):
            apply_overrides(base, {"log_level": "CHATTY"})

    def test_an_impossible_timeout_is_rejected(self, base):
        with pytest.raises(ConfigurationError):
            apply_overrides(base, {"timeouts": {"default": -5}})

    def test_an_empty_engine_name_is_rejected(self, base):
        with pytest.raises(ConfigurationError):
            apply_overrides(base, {"engine": "   "})
