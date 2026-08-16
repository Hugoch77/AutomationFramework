"""Exception hierarchy.

Every failure raised by the framework derives from :class:`AutomationError`, so callers can
catch the whole family without knowing which engine produced it.

Los mensajes van en español, igual que el resto de la documentación del proyecto: quien los lee
en un stack trace es el usuario, no un consumidor externo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from automation_framework.core.locator import Locator, Strategy


class AutomationError(Exception):
    """Base class for every error raised by the framework."""


class ConfigurationError(AutomationError):
    """Configuration is missing, malformed or contradictory."""


# --------------------------------------------------------------------------- engine ---
class EngineError(AutomationError):
    """Base class for engine lifecycle and registration problems."""


class EngineNotRegisteredError(EngineError):
    """Asked the registry for an engine name that nobody registered."""

    def __init__(self, name: str, available: Iterable[str] = ()) -> None:
        self.name = name
        self.available = tuple(available)
        known = ", ".join(repr(item) for item in self.available) or "ninguno"
        super().__init__(
            f"No hay ningún engine registrado como {name!r}. Disponibles: {known}. "
            "¿Falta importar el paquete del engine, o instalar su extra opcional?"
        )


class EngineAlreadyRegisteredError(EngineError):
    """Tried to register a name that is already taken."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Ya hay un engine registrado como {name!r}. "
            "Usa un nombre distinto, o pasa replace=True si la sustitución es intencionada."
        )


class EngineNotStartedError(EngineError):
    """Used an engine before calling ``start()``.

    Catching this early gives a readable message instead of an ``AttributeError`` on some
    half-initialised driver object deep inside the engine.
    """

    def __init__(self, engine_name: str, operation: str) -> None:
        self.engine_name = engine_name
        self.operation = operation
        super().__init__(
            f"El engine {engine_name!r} no está arrancado; no se puede ejecutar {operation!r}. "
            "Llama a start() o usa el engine como context manager."
        )


class NavigationError(EngineError):
    """The application could not be taken to the requested place.

    Lives in ``core`` rather than in the web engine because "navigation" is not a Playwright
    idea: a desktop engine that opens a window or walks a wizard has the same failure. Keeping
    it here is what lets a suite catch it without importing from ``engines``.
    """


# -------------------------------------------------------------------------- element ---
class ElementError(AutomationError):
    """Base class for problems interacting with an element."""


class ElementNotFoundError(ElementError):
    """The element never showed up within the allotted time."""

    def __init__(self, locator: Locator, timeout: float | None = None) -> None:
        self.locator = locator
        self.timeout = timeout
        waited = f" tras esperar {timeout:g}s" if timeout is not None else ""
        super().__init__(f"No se encontró el elemento {locator}{waited}.")


# ---------------------------------------------------------------------------- pages ---
class PageNotLoadedError(AutomationError):
    """A page object was used before the screen it describes was on display.

    Raised instead of letting the test fail on whichever element it happened to touch first:
    "no se encontró el botón de comprar" sends the reader looking at that button, when the real
    story is that the application was still on the previous screen.
    """

    def __init__(self, page_name: str, marker: Locator, timeout: float | None = None) -> None:
        self.page_name = page_name
        self.marker = marker
        self.timeout = timeout
        waited = f" tras esperar {timeout:g}s" if timeout is not None else ""
        super().__init__(
            f"La página {page_name!r} no llegó a cargarse{waited}: "
            f"no apareció su marcador {marker}."
        )


# ------------------------------------------------------------------------ contratos ---
class UnsupportedStrategyError(AutomationError):
    """The engine cannot resolve this kind of locator.

    Failing here, at lookup time, is deliberate: a ``Strategy.CSS`` locator handed to the
    desktop engine is a design mistake, and it should surface as such instead of as a
    mysterious "element not found" ten seconds later.
    """

    def __init__(self, engine_name: str, strategy: Strategy, supported: Iterable[Strategy]) -> None:
        self.engine_name = engine_name
        self.strategy = strategy
        self.supported = tuple(supported)
        options = ", ".join(sorted(item.value for item in self.supported)) or "ninguna"
        super().__init__(
            f"El engine {engine_name!r} no soporta la estrategia {strategy.value!r}. "
            f"Soportadas: {options}."
        )


class UnsupportedOperationError(AutomationError):
    """The operation makes no sense for this technology.

    Raised instead of silently doing nothing, which would turn a missing capability into a
    test that passes for the wrong reason.
    """

    def __init__(self, engine_name: str, operation: str, hint: str | None = None) -> None:
        self.engine_name = engine_name
        self.operation = operation
        suffix = f" {hint}" if hint else ""
        super().__init__(
            f"El engine {engine_name!r} no soporta la operación {operation!r}.{suffix}"
        )


# ---------------------------------------------------------------------------- waits ---
class WaitTimeoutError(AutomationError):
    """A wait condition never became true.

    Deliberately not derived from the builtin ``TimeoutError``: a bare ``except TimeoutError``
    somewhere in user code should not swallow framework waits.
    """

    def __init__(self, description: str, timeout: float) -> None:
        self.description = description
        self.timeout = timeout
        super().__init__(f"Se agotó la espera de {timeout:g}s para: {description}.")
