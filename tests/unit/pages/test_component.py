"""Tests for components and the relative search they rest on.

The property that matters: a component's locators are resolved **inside its root**. If they
leak to the whole screen, a class describing "a row" silently answers about the first row on
the page no matter which one it was anchored to — a bug that produces green tests, which is
the worst kind.
"""

import pytest

from automation_framework.core.locator import Locator
from automation_framework.pages import BasePage, Component, expect_text
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

TABLA = Locator.test_id("tabla", description="tabla de productos")
FILA = Locator.css("tr.fila", description="fila de producto")
NOMBRE = Locator.css(".nombre", description="nombre del producto")
PRECIO = Locator.css(".precio", description="precio del producto")
COMPRAR = Locator.css("button.comprar", description="botón de comprar")


class FilaProducto(Component):
    """Una fila de la tabla, que responde sobre sí misma."""

    def nombre(self) -> str:
        return self.find(NOMBRE).text()

    def precio(self) -> str:
        return self.find(PRECIO).text()

    def comprar(self) -> None:
        self.find(COMPRAR).click()


class PaginaConTabla(BasePage):
    @property
    def marker(self):
        return TABLA

    def filas(self):
        return self.components(FilaProducto, FILA)


@pytest.fixture
def engine():
    with FakeEngine() as instance:
        yield instance


@pytest.fixture
def pagina_con_dos_filas(engine):
    """Dos filas con los MISMOS locators internos y distinto contenido.

    Ese es el escenario donde una búsqueda no acotada pasa desapercibida: ambas filas casan
    con `.nombre`, así que un scoping roto devuelve siempre la primera y parece funcionar.
    """
    primera = engine.add(FILA, text="fila 1")
    primera.add_child(NOMBRE, text="Mochila")
    primera.add_child(PRECIO, text="29,99 €")
    primera.add_child(COMPRAR, text="Comprar")

    segunda = engine.add(FILA, text="fila 2")
    segunda.add_child(NOMBRE, text="Bicicleta")
    segunda.add_child(PRECIO, text="150,00 €")
    segunda.add_child(COMPRAR, text="Comprar")

    return PaginaConTabla(engine)


class TestBusquedaRelativa:
    def test_un_elemento_encuentra_a_sus_descendientes(self, engine):
        fila = engine.add(FILA, text="fila")
        fila.add_child(NOMBRE, text="Mochila")

        assert engine.find(FILA).find(NOMBRE).text() == "Mochila"

    def test_no_encuentra_lo_que_no_cuelga_de_el(self, engine):
        """Acotar significa acotar: un hermano no es alcanzable desde aquí."""
        engine.add(FILA, text="fila")
        engine.add(NOMBRE, text="suelto en la página")

        assert engine.find(FILA).find(NOMBRE).exists() is False

    def test_find_all_relativo_cuenta_solo_dentro_del_subarbol(self, engine):
        fila = engine.add(FILA, text="fila")
        fila.add_child(NOMBRE, text="uno")
        fila.add_child(NOMBRE, text="dos")
        engine.add(NOMBRE, text="fuera de la fila")

        assert len(engine.find(FILA).find_all(NOMBRE)) == 2

    def test_los_handles_hijos_siguen_siendo_perezosos(self, engine):
        """Se puede declarar el hijo antes de que el padre exista."""
        handle = engine.find(FILA).find(NOMBRE)

        fila = engine.add(FILA, text="fila")
        fila.add_child(NOMBRE, text="Mochila")

        assert handle.text() == "Mochila"

    def test_un_hijo_de_un_padre_ausente_simplemente_no_esta(self, engine):
        assert engine.find(FILA).find(NOMBRE).exists() is False


class TestComponent:
    def test_cada_componente_lee_su_propio_contenido(self, pagina_con_dos_filas):
        filas = pagina_con_dos_filas.filas()

        assert [fila.nombre() for fila in filas] == ["Mochila", "Bicicleta"]

    def test_el_segundo_componente_no_responde_por_el_primero(self, pagina_con_dos_filas):
        """La prueba de fuego del scoping."""
        assert pagina_con_dos_filas.filas()[1].precio() == "150,00 €"

    def test_hay_un_componente_por_coincidencia(self, pagina_con_dos_filas):
        assert len(pagina_con_dos_filas.filas()) == 2

    def test_actuar_sobre_un_componente_actua_sobre_su_elemento(self, pagina_con_dos_filas):
        pagina_con_dos_filas.filas()[1].comprar()

        assert ("click", str(COMPRAR)) in pagina_con_dos_filas.engine.events

    def test_find_all_del_componente_queda_acotado_a_su_raiz(self, engine):
        """Una fila con dos etiquetas no debe ver las de las demás filas."""
        primera = engine.add(FILA, text="fila 1")
        primera.add_child(NOMBRE, text="Mochila")
        primera.add_child(NOMBRE, text="alias: Backpack")
        segunda = engine.add(FILA, text="fila 2")
        segunda.add_child(NOMBRE, text="Bicicleta")

        filas = PaginaConTabla(engine).filas()

        assert len(filas[0].find_all(NOMBRE)) == 2
        assert len(filas[1].find_all(NOMBRE)) == 1

    def test_expone_su_raiz(self, pagina_con_dos_filas):
        assert pagina_con_dos_filas.filas()[0].root.text() == "fila 1"

    def test_el_repr_menciona_la_raiz(self, pagina_con_dos_filas):
        assert "fila de producto" in repr(pagina_con_dos_filas.filas()[0])

    def test_las_assertions_funcionan_sobre_un_componente(self, pagina_con_dos_filas):
        """El componente devuelve Elements normales: todo lo demás sigue valiendo."""
        expect_text(pagina_con_dos_filas.filas()[0].find(NOMBRE), "Mochila")


class TestVisibilidadDelComponente:
    def test_es_visible_cuando_su_raiz_lo_es(self, pagina_con_dos_filas):
        assert pagina_con_dos_filas.filas()[0].is_visible() is True

    def test_no_es_visible_cuando_su_raiz_esta_oculta(self, engine):
        engine.add(FILA, text="fila", visible=False)
        pagina = PaginaConTabla(engine)

        assert pagina.filas()[0].is_visible() is False

    def test_espera_a_que_aparezca(self, engine):
        fila = engine.add(FILA, text="fila", appear_after=3)
        fila.add_child(NOMBRE, text="Mochila")

        componente = FilaProducto(engine.find(FILA))

        assert componente.wait_until_visible() is componente


class TestComponenteUnico:
    def test_component_ancla_en_la_primera_coincidencia(self, pagina_con_dos_filas):
        assert pagina_con_dos_filas.component(FilaProducto, FILA).nombre() == "Mochila"
