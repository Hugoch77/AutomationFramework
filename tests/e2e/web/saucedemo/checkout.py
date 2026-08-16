"""The three checkout screens.

One page object each, rather than one "checkout" object with a mode: they show different
controls, and merging them would mean a class whose methods only work in certain states.
"""

from tests.e2e.web.saucedemo.datos import Cliente

from automation_framework.core.locator import Locator
from automation_framework.pages import BasePage


class PaginaDatosCliente(BasePage):
    """Paso 1: los datos de quien compra."""

    NOMBRE = Locator.test_id("firstName", description="campo de nombre")
    APELLIDO = Locator.test_id("lastName", description="campo de apellido")
    CODIGO_POSTAL = Locator.test_id("postalCode", description="campo de código postal")
    CONTINUAR = Locator.test_id("continue", description="botón de continuar")
    CANCELAR = Locator.test_id("cancel", description="botón de cancelar")
    ERROR = Locator.test_id("error", description="mensaje de error del formulario")

    @property
    def marker(self):
        return self.NOMBRE

    @property
    def name(self):
        return "datos del cliente"

    def rellenar(self, cliente: Cliente) -> None:
        """Vuelca los datos del cliente en el formulario.

        Recibe el objeto entero en vez de tres cadenas sueltas: cuando el formulario gane un
        campo, cambia esta función y la factory, y ni un test se entera.
        """
        self.find(self.NOMBRE).fill(cliente.nombre)
        self.find(self.APELLIDO).fill(cliente.apellido)
        self.find(self.CODIGO_POSTAL).fill(cliente.codigo_postal)

    def continuar(self) -> None:
        self.find(self.CONTINUAR).click()

    @property
    def error(self):
        return self.find(self.ERROR)


class PaginaResumenCompra(BasePage):
    """Paso 2: el resumen, con los totales."""

    ITEM = Locator.test_id("inventory-item", description="artículo del resumen")
    SUBTOTAL = Locator.test_id("subtotal-label", description="subtotal del pedido")
    IMPUESTOS = Locator.test_id("tax-label", description="impuestos del pedido")
    TOTAL = Locator.test_id("total-label", description="total del pedido")
    FINALIZAR = Locator.test_id("finish", description="botón de finalizar")

    @property
    def marker(self):
        return self.TOTAL

    @property
    def name(self):
        return "resumen de la compra"

    def subtotal(self) -> float:
        """El subtotal como número. El texto llega como ``Item total: $29.99``."""
        return self._importe(self.SUBTOTAL)

    def impuestos(self) -> float:
        return self._importe(self.IMPUESTOS)

    def total(self) -> float:
        return self._importe(self.TOTAL)

    def _importe(self, locator: Locator) -> float:
        texto = self.find(locator).text()
        return float(texto.rsplit("$", 1)[-1])

    def finalizar(self) -> None:
        self.find(self.FINALIZAR).click()


class PaginaCompraCompletada(BasePage):
    """Paso 3: la confirmación."""

    CABECERA = Locator.test_id("complete-header", description="cabecera de confirmación")
    TEXTO = Locator.test_id("complete-text", description="texto de confirmación")
    VOLVER = Locator.test_id("back-to-products", description="volver al catálogo")

    @property
    def marker(self):
        return self.CABECERA

    @property
    def name(self):
        return "compra completada"

    @property
    def cabecera(self):
        return self.find(self.CABECERA)

    def volver_al_catalogo(self) -> None:
        self.find(self.VOLVER).click()
