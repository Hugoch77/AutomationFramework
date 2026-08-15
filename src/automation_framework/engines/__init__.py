"""Concrete engine implementations.

Each engine lives in its own subpackage and registers itself on import. The automation
library it wraps is an **optional extra**, so importing an engine whose dependency is not
installed raises ``ImportError`` — which is why loading is done deliberately, never implicitly.
"""

from __future__ import annotations

import importlib

KNOWN_ENGINES = {
    "web": "automation_framework.engines.web",
    # "desktop": "automation_framework.engines.desktop",  # Fase 5
}


def load_available() -> dict[str, str | None]:
    """Import every known engine, registering the ones whose dependencies are installed.

    Returns:
        A mapping of engine name to ``None`` when it loaded, or the reason it did not.
        Failing to load is normal — the web extra is not installed on a desktop-only machine,
        and pywinauto cannot be installed on Linux at all — so this reports instead of raising.
        Asking the registry for an engine that never loaded is what produces a hard error,
        and by then the caller has actually said which one they wanted.
    """
    results: dict[str, str | None] = {}
    for name, module in KNOWN_ENGINES.items():
        try:
            importlib.import_module(module)
        except ImportError as error:
            results[name] = str(error)
        else:
            results[name] = None
    return results
