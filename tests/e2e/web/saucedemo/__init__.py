"""Page objects for saucedemo.com.

These belong to the *suite*, not to the framework: `automation_framework.pages` ships the base
class, and each application under test brings its own vocabulary. Keeping them here is what
stops the framework from ever knowing that saucedemo exists.

Locators use `data-test`, which is what the site publishes as its testing hook — the suite
configures `test_id_attribute` accordingly via `@pytest.mark.af_config`.
"""

from tests.e2e.web.saucedemo.carrito import PaginaCarrito
from tests.e2e.web.saucedemo.catalogo import PaginaCatalogo
from tests.e2e.web.saucedemo.checkout import (
    PaginaCompraCompletada,
    PaginaDatosCliente,
    PaginaResumenCompra,
)
from tests.e2e.web.saucedemo.datos import USUARIOS, Cliente, Usuario, cliente
from tests.e2e.web.saucedemo.login import PaginaLogin

__all__ = [
    "USUARIOS",
    "Cliente",
    "PaginaCarrito",
    "PaginaCatalogo",
    "PaginaCompraCompletada",
    "PaginaDatosCliente",
    "PaginaLogin",
    "PaginaResumenCompra",
    "Usuario",
    "cliente",
]
