"""The shopping cart."""

from tests.e2e.web.saucedemo.catalogo import TarjetaProducto

from automation_framework.core.locator import Locator
from automation_framework.pages import BasePage


class PaginaCarrito(BasePage):
    """Contenido del carrito, antes de pasar por caja."""

    RUTA = "/cart.html"

    TITULO = Locator.test_id("title", description="título de la pantalla")
    LISTA = Locator.test_id("cart-list", description="lista del carrito")
    ITEM = Locator.test_id("inventory-item", description="artículo del carrito")
    PASAR_POR_CAJA = Locator.test_id("checkout", description="botón de pasar por caja")
    SEGUIR_COMPRANDO = Locator.test_id("continue-shopping", description="seguir comprando")

    @property
    def marker(self):
        return self.LISTA

    @property
    def name(self):
        return "carrito"

    def articulos(self):
        """Un componente por artículo. Es la misma tarjeta que en el catálogo.

        Que la clase se reutilice tal cual entre dos pantallas es precisamente lo que un
        componente acotado permite: sus locators son relativos, no absolutos.
        """
        return self.components(TarjetaProducto, self.ITEM)

    def nombres(self) -> list[str]:
        return [articulo.nombre() for articulo in self.articulos()]

    def quitar(self, nombre: str) -> None:
        for articulo in self.articulos():
            if articulo.nombre() == nombre:
                articulo.quitar_del_carrito()
                return
        raise AssertionError(f"El carrito no contiene {nombre!r}; hay: {self.nombres()}.")

    def pasar_por_caja(self) -> None:
        self.find(self.PASAR_POR_CAJA).click()

    def seguir_comprando(self) -> None:
        self.find(self.SEGUIR_COMPRANDO).click()
