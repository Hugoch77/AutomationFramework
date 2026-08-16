"""Loading test data from files.

Credentials, customers, catalogues: the things a suite parametrises over. Keeping them in a
file rather than inline is what lets the same test run over ten cases without ten copies of
itself, and lets someone add a case without touching Python.

JSON only, deliberately. YAML reads better, but it would mean a runtime dependency for every
consumer of the framework — including the desktop engine, which has no use for it. If a suite
ever genuinely needs anchors or comments, that is the moment to reconsider, and adding a loader
here later costs nothing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from automation_framework.core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path


def load_json(path: Path) -> Any:
    """Read and parse the JSON file at ``path``.

    Raises:
        ConfigurationError: The file is missing or is not valid JSON. Both messages name the
            full path: a data file is usually resolved relative to a suite, and "no such file"
            without the path sends the reader hunting through fixtures.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigurationError(f"No se pudo leer el fichero de datos {path}: {error}") from error

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigurationError(
            f"El fichero de datos {path} no es JSON válido: {error}"
        ) from error


def load_records[T](path: Path, factory: Callable[..., T]) -> list[T]:
    """Build one object per entry in the JSON array at ``path``.

    ``factory`` is normally a dataclass. Going through one instead of handing tests raw
    dictionaries is what makes a typo fail on load — where the message can name the file —
    instead of as a ``KeyError`` in the middle of a test.

    Raises:
        ConfigurationError: The file is not a list of objects, or an entry does not match
            what ``factory`` accepts.
    """
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ConfigurationError(
            f"El fichero de datos {path} debe contener una lista, no {type(payload).__name__}."
        )

    records: list[T] = []
    for position, entry in enumerate(payload):
        if not isinstance(entry, dict):
            raise ConfigurationError(
                f"La entrada {position} de {path} debe ser un objeto, no {type(entry).__name__}."
            )
        try:
            records.append(factory(**entry))
        except TypeError as error:
            raise ConfigurationError(
                f"La entrada {position} de {path} no encaja con "
                f"{getattr(factory, '__name__', factory)!r}: {error}"
            ) from error
    return records


def load_mapping[T](path: Path, factory: Callable[..., T]) -> dict[str, T]:
    """Build one object per entry in the JSON object at ``path``, keyed by its name.

    The shape to reach for when tests refer to a case by name (``usuarios["bloqueado"]``)
    rather than iterating over all of them.

    Raises:
        ConfigurationError: The file is not an object, or an entry does not match ``factory``.
    """
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ConfigurationError(
            f"El fichero de datos {path} debe contener un objeto, no {type(payload).__name__}."
        )

    records: dict[str, T] = {}
    for key, entry in payload.items():
        if not isinstance(entry, dict):
            raise ConfigurationError(
                f"La entrada {key!r} de {path} debe ser un objeto, no {type(entry).__name__}."
            )
        try:
            records[key] = factory(**entry)
        except TypeError as error:
            raise ConfigurationError(
                f"La entrada {key!r} de {path} no encaja con "
                f"{getattr(factory, '__name__', factory)!r}: {error}"
            ) from error
    return records


def data_path(anchor: Path, *parts: str) -> Path:
    """Resolve a data file relative to the module that owns it.

    Called as ``data_path(Path(__file__), "datos", "usuarios.json")``, so a suite finds its
    own data no matter which directory pytest was launched from — the usual cause of files
    that load locally and vanish in CI.
    """
    return anchor.resolve().parent.joinpath(*parts)


def merged(base: Mapping[str, Any], *overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Combine dictionaries left to right, for building a case out of a shared default.

    The building block of a factory: one valid record in the file, and each test states only
    the field it cares about, so a test about a missing postcode does not also have to spell
    out a name and a surname that have nothing to do with it.
    """
    result = dict(base)
    for override in overrides:
        result.update(override)
    return result


def ids_for(records: Sequence[Any], attribute: str = "id") -> list[str]:
    """Readable ids for ``pytest.mark.parametrize``.

    Without them a parametrised failure reports ``test_login[record12]``, and finding out
    which case broke means counting entries in the file.
    """
    return [str(getattr(record, attribute, record)) for record in records]
