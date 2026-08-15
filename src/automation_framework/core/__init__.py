"""Technology-agnostic contracts of the framework.

Nothing in this package may import an automation library (Playwright, pywinauto, ...)
nor the ``engines`` package. Concrete implementations register themselves at runtime
through :mod:`automation_framework.core.registry`.

That rule is enforced by ``tests/arch/test_layering.py``, not by convention.

This module re-exports the public surface, so suites and engines import from one place::

    from automation_framework.core import Locator, Strategy, create_engine
"""

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.config import Settings, Timeouts, get_settings, load_settings
from automation_framework.core.element import Element, ElementState
from automation_framework.core.engine import Engine
from automation_framework.core.exceptions import (
    AutomationError,
    ConfigurationError,
    ElementError,
    ElementNotFoundError,
    EngineAlreadyRegisteredError,
    EngineError,
    EngineNotRegisteredError,
    EngineNotStartedError,
    UnsupportedOperationError,
    UnsupportedStrategyError,
    WaitTimeoutError,
)
from automation_framework.core.locator import Locator, Strategy
from automation_framework.core.log import bound_context, configure_logging, get_logger
from automation_framework.core.registry import (
    available_engines,
    create_engine,
    is_registered,
    register_engine,
)
from automation_framework.core.waits import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIMEOUT,
    wait_until,
    wait_while,
)

__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_TIMEOUT",
    "AutomationError",
    "Capabilities",
    "ConfigurationError",
    "Element",
    "ElementError",
    "ElementNotFoundError",
    "ElementState",
    "Engine",
    "EngineAlreadyRegisteredError",
    "EngineError",
    "EngineNotRegisteredError",
    "EngineNotStartedError",
    "Feature",
    "Locator",
    "Settings",
    "Strategy",
    "Timeouts",
    "UnsupportedOperationError",
    "UnsupportedStrategyError",
    "WaitTimeoutError",
    "available_engines",
    "bound_context",
    "configure_logging",
    "create_engine",
    "get_logger",
    "get_settings",
    "is_registered",
    "load_settings",
    "register_engine",
    "wait_until",
    "wait_while",
]
