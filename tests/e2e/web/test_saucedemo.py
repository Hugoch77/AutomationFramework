"""Suite de negocio sobre saucedemo.com.

Estos tests hablan de comprar, no de hacer clic: toda la mecánica vive en los Page Objects de
`saucedemo/`. Si el sitio cambia el marcado, se arregla ahí y ni un solo test se toca — que es
justamente lo que la Fase 3 tenía que demostrar.

Marcados `external`: dependen de un sitio de terceros, así que su job de CI no bloquea. Un
saucedemo.com caído no es una regresión de este código.
"""

import pytest
from tests.e2e.web.saucedemo import (
    USUARIOS,
    PaginaCarrito,
    PaginaCatalogo,
    PaginaCompraCompletada,
    PaginaDatosCliente,
    PaginaLogin,
    PaginaResumenCompra,
    cliente,
)

from automation_framework.pages import (
    expect_count,
    expect_hidden,
    expect_text,
    expect_text_containing,
    expect_value,
    expect_visible,
)
from automation_framework.utils import ids_for

SITIO = "https://www.saucedemo.com"

pytestmark = [
    pytest.mark.web,
    pytest.mark.external,
    pytest.mark.slow,
    pytest.mark.af_config(
        base_url=SITIO,
        # saucedemo publica sus hooks como data-test, no como data-testid.
        test_id_attribute="data-test",
        # La primera navegación se trae todos los assets por la red de turno y se pasa de los
        # 10s por defecto. Sólo se amplía el presupuesto de navegación: las esperas de
        # elemento siguen cortas, para que un fallo real se reporte rápido.
        timeouts={"navigation": 60},
    ),
]

ESTANDAR = USUARIOS["estandar"]
USUARIO = ESTANDAR.usuario
CLAVE = ESTANDAR.clave
MOCHILA = "Sauce Labs Backpack"
CAMISETA = "Sauce Labs Bolt T-Shirt"

QUE_ENTRAN = [usuario for usuario in USUARIOS.values() if usuario.puede_entrar]
QUE_NO_ENTRAN = [usuario for usuario in USUARIOS.values() if not usuario.puede_entrar]


@pytest.fixture
def login(engine):
    """La pantalla de login, ya abierta."""
    return PaginaLogin(engine).abrir()


@pytest.fixture
def catalogo(login):
    """Sesión iniciada y catálogo en pantalla, que es el punto de partida de casi todo."""
    login.entrar_como(USUARIO, CLAVE)
    return PaginaCatalogo(login.engine).wait_until_loaded()


@pytest.mark.smoke
class TestLogin:
    def test_un_usuario_valido_entra_al_catalogo(self, login):
        login.entrar_como(USUARIO, CLAVE)

        catalogo = PaginaCatalogo(login.engine).wait_until_loaded()

        expect_text(catalogo.find(catalogo.TITULO), "Products")
        expect_count(catalogo.engine, catalogo.ITEM, 6)

    @pytest.mark.parametrize("caso", QUE_NO_ENTRAN, ids=ids_for(QUE_NO_ENTRAN))
    def test_quien_no_debe_entrar_se_queda_fuera(self, login, caso):
        """Cada motivo de rechazo tiene su propio mensaje: son fallos distintos.

        Parametrizado desde `datos/usuarios.json`, así que añadir un caso nuevo no toca
        este archivo.
        """
        login.entrar_como(caso.usuario, caso.clave)

        expect_text_containing(login.error, caso.error_esperado)
        assert PaginaCatalogo(login.engine).is_loaded() is False

    @pytest.mark.parametrize("caso", QUE_ENTRAN, ids=ids_for(QUE_ENTRAN))
    def test_quien_debe_entrar_llega_al_catalogo(self, login, caso):
        """Incluye al usuario lento: si la espera del framework no fuera explícita, ese
        caso fallaría y el resto pasaría, que es la definición de suite frágil."""
        login.entrar_como(caso.usuario, caso.clave)

        PaginaCatalogo(login.engine).wait_until_loaded()

    def test_la_contrasena_no_se_muestra_en_claro(self, login):
        login.find(login.CLAVE).fill(CLAVE)

        assert login.find(login.CLAVE).attribute("type") == "password"

    def test_lo_tecleado_llega_al_campo(self, login):
        """`value()` lee lo que el usuario escribió, no el atributo declarado en el HTML."""
        login.find(login.USUARIO).fill(USUARIO)

        expect_value(login.find(login.USUARIO), USUARIO)


class TestCatalogo:
    def test_muestra_los_seis_productos(self, catalogo):
        assert len(catalogo.productos()) == 6

    def test_cada_producto_tiene_nombre_y_precio(self, catalogo):
        """Comprueba el acotado de los componentes: seis nombres distintos, no seis veces uno."""
        nombres = catalogo.nombres()

        assert len(set(nombres)) == 6
        assert all(precio > 0 for precio in catalogo.precios())

    def test_ordenar_por_precio_ascendente_reordena_el_listado(self, catalogo):
        catalogo.ordenar_por("lohi")

        precios = catalogo.precios()

        assert precios == sorted(precios)

    def test_ordenar_por_nombre_descendente_reordena_el_listado(self, catalogo):
        catalogo.ordenar_por("za")

        nombres = catalogo.nombres()

        assert nombres == sorted(nombres, reverse=True)

    def test_el_carrito_empieza_vacio(self, catalogo):
        expect_hidden(catalogo.contador_del_carrito)


class TestCarrito:
    def test_anadir_un_producto_actualiza_el_contador(self, catalogo):
        catalogo.producto(MOCHILA).anadir_al_carrito()

        expect_text(catalogo.contador_del_carrito, "1")

    def test_el_boton_del_producto_pasa_a_ofrecer_quitarlo(self, catalogo):
        producto = catalogo.producto(MOCHILA)

        producto.anadir_al_carrito()

        assert producto.texto_del_boton().lower() == "remove"

    def test_el_carrito_contiene_lo_que_se_anadio(self, catalogo):
        catalogo.producto(MOCHILA).anadir_al_carrito()
        catalogo.producto(CAMISETA).anadir_al_carrito()
        catalogo.ir_al_carrito()

        carrito = PaginaCarrito(catalogo.engine).wait_until_loaded()

        assert sorted(carrito.nombres()) == sorted([MOCHILA, CAMISETA])

    def test_quitar_un_articulo_lo_saca_del_carrito(self, catalogo):
        catalogo.producto(MOCHILA).anadir_al_carrito()
        catalogo.producto(CAMISETA).anadir_al_carrito()
        catalogo.ir_al_carrito()
        carrito = PaginaCarrito(catalogo.engine).wait_until_loaded()

        carrito.quitar(MOCHILA)

        assert carrito.nombres() == [CAMISETA]


@pytest.mark.smoke
class TestCompra:
    def test_una_compra_completa_llega_a_la_confirmacion(self, catalogo):
        """El recorrido de negocio de punta a punta, que es lo que de verdad importa."""
        catalogo.producto(MOCHILA).anadir_al_carrito()
        catalogo.ir_al_carrito()

        carrito = PaginaCarrito(catalogo.engine).wait_until_loaded()
        carrito.pasar_por_caja()

        datos = PaginaDatosCliente(catalogo.engine).wait_until_loaded()
        datos.rellenar(cliente())
        datos.continuar()

        resumen = PaginaResumenCompra(catalogo.engine).wait_until_loaded()
        resumen.finalizar()

        completada = PaginaCompraCompletada(catalogo.engine).wait_until_loaded()
        expect_text_containing(completada.cabecera, "Thank you")

    def test_el_total_suma_el_subtotal_y_los_impuestos(self, catalogo):
        catalogo.producto(MOCHILA).anadir_al_carrito()
        catalogo.producto(CAMISETA).anadir_al_carrito()
        catalogo.ir_al_carrito()

        PaginaCarrito(catalogo.engine).wait_until_loaded().pasar_por_caja()
        datos = PaginaDatosCliente(catalogo.engine).wait_until_loaded()
        datos.rellenar(cliente())
        datos.continuar()

        resumen = PaginaResumenCompra(catalogo.engine).wait_until_loaded()

        assert resumen.total() == pytest.approx(resumen.subtotal() + resumen.impuestos(), abs=0.01)

    @pytest.mark.parametrize(
        ("falta", "mensaje"),
        [
            ("nombre", "First Name is required"),
            ("apellido", "Last Name is required"),
            ("codigo_postal", "Postal Code is required"),
        ],
    )
    def test_el_checkout_exige_cada_dato_del_cliente(self, catalogo, falta, mensaje):
        """La factory deja declarar sólo el campo que importa: los otros dos son válidos y
        el test no tiene que deletrearlos."""
        catalogo.producto(MOCHILA).anadir_al_carrito()
        catalogo.ir_al_carrito()
        PaginaCarrito(catalogo.engine).wait_until_loaded().pasar_por_caja()

        datos = PaginaDatosCliente(catalogo.engine).wait_until_loaded()
        datos.rellenar(cliente(**{falta: ""}))
        datos.continuar()

        expect_text_containing(datos.error, mensaje)


class TestSesion:
    def test_salir_devuelve_al_login(self, catalogo):
        catalogo.salir()

        expect_visible(PaginaLogin(catalogo.engine).find(PaginaLogin.ENTRAR))
