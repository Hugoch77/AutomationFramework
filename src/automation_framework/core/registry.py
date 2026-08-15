"""Where engines are looked up by name.

This is the seam that keeps ``core`` free of automation libraries. Nothing here imports a
concrete engine: each engine package registers itself when imported, and callers ask for one
by name::

    engine = create_engine("web", headless=False)

Without this indirection ``core`` would need ``from ..engines.web import PlaywrightEngine``,
and the whole layering guarantee would collapse.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from automation_framework.core.engine import Engine
from automation_framework.core.exceptions import (
    EngineAlreadyRegisteredError,
    EngineError,
    EngineNotRegisteredError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Alias perezoso (PEP 695): `Callable` sólo se importa bajo TYPE_CHECKING, así que un alias
# evaluado en runtime fallaría al importar el módulo.
type EngineFactory = Callable[..., Engine]
"""Anything that builds an engine: the class itself, or a function that configures one."""

_REGISTRY: dict[str, EngineFactory] = {}


def _normalise(name: str) -> str:
    """Engine names are case- and whitespace-insensitive; ``"Web"`` and ``"web"`` are one."""
    return name.strip().lower()


def _validated(name: str) -> str:
    """Normalise ``name`` and reject it if nothing is left.

    Used by the operations that take a name as a real argument. Without this, an empty name
    reaches the registry lookup and comes back as "no engine registered as ''", which sends
    the reader hunting for a missing import instead of at the empty string they passed.
    """
    key = _normalise(name)
    if not key:
        raise ValueError("El nombre de un engine no puede estar vacío.")
    return key


def register_engine(name: str, factory: EngineFactory, *, replace: bool = False) -> None:
    """Make ``factory`` available under ``name``.

    Args:
        name: Short identifier such as ``"web"`` or ``"desktop"``.
        factory: Callable returning an :class:`~automation_framework.core.engine.Engine`.
        replace: Allow overwriting an existing registration. Off by default so that a name
            collision between two engines surfaces instead of one silently shadowing the other.

    Raises:
        ValueError: ``name`` is empty.
        EngineAlreadyRegisteredError: ``name`` is taken and ``replace`` is false.
    """
    key = _validated(name)
    if key in _REGISTRY and not replace:
        raise EngineAlreadyRegisteredError(key)
    _REGISTRY[key] = factory


def unregister_engine(name: str) -> None:
    """Remove ``name`` from the registry. Silent if it was not there."""
    _REGISTRY.pop(_normalise(name), None)


def is_registered(name: str) -> bool:
    """Whether ``name`` currently resolves to an engine."""
    return _normalise(name) in _REGISTRY


def available_engines() -> tuple[str, ...]:
    """Every registered engine name, sorted."""
    return tuple(sorted(_REGISTRY))


def clear_registry() -> None:
    """Empty the registry.

    For tests. The registry is process-global, so a suite that registers doubles must put it
    back the way it found it.
    """
    _REGISTRY.clear()


def create_engine(name: str, **options: Any) -> Engine:
    """Build the engine registered as ``name``, passing ``options`` to its factory.

    Raises:
        ValueError: ``name`` is empty. Same rule as :func:`register_engine`, so that an empty
            name is never mistaken for a missing registration.
        EngineNotRegisteredError: Nobody registered that name. The message lists what is
            available, which is usually enough to spot the missing import.
        EngineError: The factory returned something that is not an engine.
    """
    key = _validated(name)
    try:
        factory = _REGISTRY[key]
    except KeyError:
        raise EngineNotRegisteredError(key, available_engines()) from None

    engine = factory(**options)

    # Una factory mal escrita se detecta aquí y no tres llamadas más tarde, cuando el
    # AttributeError ya no dice nada del sitio donde estaba el error.
    if not isinstance(engine, Engine):
        raise EngineError(
            f"La factory registrada como {key!r} devolvió {type(engine).__name__}, "
            "que no es un Engine."
        )
    return engine
