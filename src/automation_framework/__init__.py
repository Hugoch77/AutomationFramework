"""Multi-engine automation framework.

The package is layered so that test code never depends on a concrete automation
technology. See ``README.md`` for the rationale.

Layers (dependencies always point downwards):

    tests/e2e  ->  pages  ->  core  <-  engines (web, desktop, ...)

``core`` holds the abstract contracts and must never import from ``engines``.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
