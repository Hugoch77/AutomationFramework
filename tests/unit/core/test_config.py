"""Tests for the layered configuration."""

from pathlib import Path

import pytest

from automation_framework.core.config import (
    Settings,
    Timeouts,
    get_settings,
    load_settings,
    reset_settings,
)
from automation_framework.core.exceptions import ConfigurationError

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch, tmp_path):
    """Isolate from the developer's real environment and from any .env on disk."""
    for name in list(__import__("os").environ):
        if name.startswith("AF_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    reset_settings()
    yield
    reset_settings()


class TestDefaults:
    def test_are_safe_for_ci(self):
        """Headless on and capture on: the settings a pipeline needs, without configuring."""
        settings = load_settings()

        assert settings.headless is True
        assert settings.capture_on_failure is True

    def test_cover_every_field(self):
        settings = load_settings()

        assert settings.engine == "web"
        assert settings.base_url is None
        assert settings.artifacts_dir == Path("artifacts")
        assert settings.log_level == "INFO"
        assert settings.log_json is False

    def test_timeouts_have_their_own_defaults(self):
        timeouts = load_settings().timeouts

        assert timeouts.default == 10.0
        assert timeouts.poll_interval == 0.1
        assert timeouts.startup == 30.0


class TestEnvironment:
    def test_reads_prefixed_variables(self, monkeypatch):
        monkeypatch.setenv("AF_ENGINE", "desktop")
        monkeypatch.setenv("AF_HEADLESS", "false")
        monkeypatch.setenv("AF_BASE_URL", "https://ejemplo.test")

        settings = load_settings()

        assert settings.engine == "desktop"
        assert settings.headless is False
        assert settings.base_url == "https://ejemplo.test"

    def test_reads_nested_values_with_a_double_underscore(self, monkeypatch):
        monkeypatch.setenv("AF_TIMEOUTS__DEFAULT", "45")

        assert load_settings().timeouts.default == 45.0

    def test_a_nested_override_keeps_the_other_defaults(self, monkeypatch):
        monkeypatch.setenv("AF_TIMEOUTS__DEFAULT", "45")

        assert load_settings().timeouts.poll_interval == 0.1

    def test_ignores_unprefixed_variables(self, monkeypatch):
        monkeypatch.setenv("ENGINE", "desktop")

        assert load_settings().engine == "web"

    def test_reads_an_env_file(self, tmp_path):
        (tmp_path / ".env").write_text("AF_ENGINE=desktop\nAF_HEADLESS=false\n", encoding="utf-8")

        settings = load_settings()

        assert settings.engine == "desktop"
        assert settings.headless is False

    def test_environment_wins_over_the_env_file(self, tmp_path, monkeypatch):
        """CI sets variables; it must not have to rewrite a file that is not in the repo."""
        (tmp_path / ".env").write_text("AF_ENGINE=desktop\n", encoding="utf-8")
        monkeypatch.setenv("AF_ENGINE", "web")

        assert load_settings().engine == "web"


class TestOverrides:
    def test_explicit_arguments_win_over_everything(self, monkeypatch):
        monkeypatch.setenv("AF_ENGINE", "desktop")

        assert load_settings(engine="fake").engine == "fake"


class TestValidation:
    def test_the_log_level_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("AF_LOG_LEVEL", "debug")

        assert load_settings().log_level == "DEBUG"

    def test_an_invalid_log_level_is_rejected(self, monkeypatch):
        monkeypatch.setenv("AF_LOG_LEVEL", "CHATTY")

        with pytest.raises(ConfigurationError, match="Nivel de log inválido"):
            load_settings()

    def test_the_engine_name_is_normalised(self, monkeypatch):
        monkeypatch.setenv("AF_ENGINE", "  DESKTOP  ")

        assert load_settings().engine == "desktop"

    def test_an_empty_engine_name_is_rejected(self, monkeypatch):
        monkeypatch.setenv("AF_ENGINE", "   ")

        with pytest.raises(ConfigurationError, match="no puede estar vacío"):
            load_settings()

    @pytest.mark.parametrize("field", ["DEFAULT", "POLL_INTERVAL", "STARTUP"])
    def test_timeouts_must_be_positive(self, monkeypatch, field):
        monkeypatch.setenv(f"AF_TIMEOUTS__{field}", "0")

        with pytest.raises(ConfigurationError):
            load_settings()

    def test_an_unknown_setting_is_rejected(self, monkeypatch):
        """Catches typos: AF_HEADLES would otherwise be silently ignored."""
        monkeypatch.setenv("AF_HEADLES", "true")

        with pytest.raises(ConfigurationError):
            load_settings()

    def test_the_error_names_the_offending_field(self, monkeypatch):
        monkeypatch.setenv("AF_LOG_LEVEL", "CHATTY")

        with pytest.raises(ConfigurationError, match="log_level"):
            load_settings()

    def test_a_non_string_log_level_is_rejected_without_crashing_the_validator(self):
        """The normaliser must pass odd types through, not blow up trying to upper() them."""
        with pytest.raises(ConfigurationError):
            load_settings(log_level=123)

    def test_the_pydantic_error_is_kept_as_the_cause(self, monkeypatch):
        monkeypatch.setenv("AF_LOG_LEVEL", "CHATTY")

        with pytest.raises(ConfigurationError) as excinfo:
            load_settings()

        assert excinfo.value.__cause__ is not None


class TestCaching:
    def test_get_settings_returns_the_same_object(self):
        assert get_settings() is get_settings()

    def test_configuration_does_not_change_mid_run(self, monkeypatch):
        """A suite where half the tests read one timeout is not reproducible."""
        first = get_settings()
        monkeypatch.setenv("AF_ENGINE", "desktop")

        assert get_settings() is first

    def test_reset_makes_the_next_read_pick_up_the_environment(self, monkeypatch):
        get_settings()
        monkeypatch.setenv("AF_ENGINE", "desktop")

        reset_settings()

        assert get_settings().engine == "desktop"


class TestModels:
    def test_timeouts_can_be_built_directly(self):
        assert Timeouts(default=5).default == 5.0

    def test_settings_can_be_built_directly(self):
        assert Settings(engine="fake").engine == "fake"
