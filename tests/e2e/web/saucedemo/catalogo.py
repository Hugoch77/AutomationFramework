"""The product catalogue, and the card component it is made of."""

from automation_framework.core.locator import Locator
from automation_framework.pages import BasePage, Component


class TarjetaProducto(Component):
    """Una tarjeta del catálogo.

    Sus locators son relativos a la tarjeta, así que la misma clase sirve para cualquiera de
    los seis productos sin saber en qué posición está. Sin búsqueda acotada haría falta un
    XPath por producto que codificara la estructura de la página entera.
    """

    NOMBRE = Locator.test_id("inventory-item-name", description="nombre del producto")
    PRECIO = Locator.test_id("inventory-item-price", description="precio del producto")
    BOTON = Locator.css("button", description="botón de añadir o quitar del carrito")

    def nombre(self) -> str:
        return self.find(self.NOMBRE).text()

    def precio(self) -> str:
        return self.find(self.PRECIO).text()

    def anadir_al_carrito(self) -> None:
        self.find(self.BOTON).click()

    def quitar_del_carrito(self) -> None:
        self.find(self.BOTON).click()

    def texto_del_boton(self) -> str:
        return self.find(self.BOTON).text()


class PaginaCatalogo(BasePage):
    """Listado de productos, la pantalla a la que lleva un login correcto."""

    RUTA = "/inventory.html"

    TITULO = Locator.test_id("title", description="título de la pantalla")
    ITEM = Locator.test_id("inventory-item", description="tarjeta de producto")
    CARRITO = Locator.test_id("shopping-cart-link", description="acceso al carrito")
    CONTADOR = Locator.test_id("shopping-cart-badge", description="contador del carrito")
    ORDENAR = Locator.test_id("product-sort-container", description="selector de orden")
    MENU = Locator.css("#react-burger-menu-btn", description="botón del menú lateral")
    SALIR = Locator.test_id("logout-sidebar-link", description="enlace de salir")

    @property
    def marker(self):
        return self.ITEM

    @property
    def name(self):
        return "catálogo"

    # ------------------------------------------------------------------ productos ---

    def productos(self):
        """Una tarjeta por producto, en el orden en que se muestran."""
        return self.components(TarjetaProducto, self.ITEM)

    def producto(self, nombre: str) -> TarjetaProducto:
        """La tarjeta cuyo nombre es ``nombre``.

        Raises:
            AssertionError: No hay ningún producto con ese nombre. Es un fallo del test
                —pidió algo que el catálogo no tiene— y así lo reporta pytest.
        """
        for tarjeta in self.productos():
            if tarjeta.nombre() == nombre:
                return tarjeta
        disponibles = ", ".join(repr(tarjeta.nombre()) for tarjeta in self.productos())
        raise AssertionError(f"No hay ningún producto llamado {nombre!r}. Hay: {disponibles}.")

    def nombres(self) -> list[str]:
        return [tarjeta.nombre() for tarjeta in self.productos()]

    def precios(self) -> list[float]:
        """Los precios como números, para poder comprobar que un orden es el pedido."""
        return [float(tarjeta.precio().removeprefix("$")) for tarjeta in self.productos()]

    def ordenar_por(self, criterio: str) -> None:
        """Cambia el orden del listado. ``criterio`` es el valor del desplegable (``lohi``…)."""
        self.find(self.ORDENAR).select(criterio)

    # -------------------------------------------------------------------- carrito ---

    @property
    def contador_del_carrito(self):
        """El globo con el número de artículos. No existe cuando el carrito está vacío."""
        return self.find(self.CONTADOR)

    def ir_al_carrito(self) -> None:
        self.find(self.CARRITO).click()

    # -------------------------------------------------------------------- sesión ---

    def salir(self) -> None:
        self.find(self.MENU).click()
        self.find(self.SALIR).click()
