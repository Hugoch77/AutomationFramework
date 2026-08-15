"""Tests for the capability declaration."""

import pytest

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.locator import Strategy

pytestmark = pytest.mark.unit


class TestConstruction:
    def test_of_freezes_whatever_iterable_it_gets(self):
        capabilities = Capabilities.of(
            "web", strategies=[Strategy.CSS, Strategy.CSS], features=[Feature.TRACING]
        )

        assert capabilities.strategies == frozenset({Strategy.CSS})
        assert capabilities.features == frozenset({Feature.TRACING})

    def test_features_are_optional(self):
        assert Capabilities.of("web", strategies=[Strategy.CSS]).features == frozenset()

    def test_keeps_the_name(self):
        assert Capabilities.of("web", strategies=[]).name == "web"

    def test_is_frozen(self):
        capabilities = Capabilities.of("web", strategies=[Strategy.CSS])

        with pytest.raises(AttributeError):
            capabilities.name = "otro"  # type: ignore[misc]


class TestQueries:
    @pytest.fixture
    def capabilities(self):
        return Capabilities.of(
            "desktop",
            strategies=[Strategy.AUTOMATION_ID, Strategy.NAME],
            features=[Feature.SCREENSHOT, Feature.ATTACH_TO_RUNNING],
        )

    def test_supports_declared_strategies(self, capabilities):
        assert capabilities.supports(Strategy.AUTOMATION_ID) is True
        assert capabilities.supports(Strategy.NAME) is True

    def test_does_not_support_undeclared_ones(self, capabilities):
        assert capabilities.supports(Strategy.CSS) is False

    def test_has_declared_features(self, capabilities):
        assert capabilities.has(Feature.SCREENSHOT) is True
        assert capabilities.has(Feature.ATTACH_TO_RUNNING) is True

    def test_does_not_have_undeclared_ones(self, capabilities):
        assert capabilities.has(Feature.TRACING) is False

    def test_an_engine_declaring_nothing_supports_nothing(self):
        empty = Capabilities.of("vacío", strategies=[])

        assert empty.supports(Strategy.CSS) is False
        assert empty.has(Feature.SCREENSHOT) is False
