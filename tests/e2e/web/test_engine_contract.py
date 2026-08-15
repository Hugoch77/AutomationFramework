"""The web engine driving a real browser against real HTML.

These are the tests that decide whether the Fase 1 abstractions actually hold up. The core
was validated against a dictionary; here the same contract runs through Chromium.

Deliberately no sleeps anywhere: `index.html` scripts an element to appear after 400ms and
another to disappear, and the auto-waiting inherited from `Element` has to cope on its own.
"""

import pytest

from automation_framework.core.element import ElementState
from automation_framework.core.exceptions import (
    ElementError,
    ElementNotFoundError,
    UnsupportedStrategyError,
    WaitTimeoutError,
)
from automation_framework.core.locator import Locator, Strategy

pytestmark = [pytest.mark.web]

TITULO = Locator.test_id("titulo", description="título de la página")
CAJA = Locator.test_id("caja-busqueda", description="caja de búsqueda")
BOTON = Locator.test_id("boton-buscar", description="botón de buscar")
RESULTADO = Locator.test_id("resultado", description="resultado de la búsqueda")
OCULTO = Locator.test_id("oculto", description="párrafo oculto")
TARDIO = Locator.test_id("tardio", description="elemento que aparece tarde")
EFIMERO = Locator.test_id("efimero", description="elemento que desaparece")
AUSENTE = Locator.test_id("no-existe", description="algo que no está")
FILAS = Locator.css("li.fila", description="filas de la lista")


@pytest.fixture
def web(engine, local_site):
    engine.goto(f"{local_site}/index.html")
    return engine


class TestLocalizacion:
    """Cada estrategia declarada en las capabilities tiene que resolver de verdad."""

    def test_por_test_id(self, web):
        assert web.find(TITULO).text() == "Banco de pruebas"

    def test_por_css(self, web):
        assert web.find(Locator.css("h1")).text() == "Banco de pruebas"

    def test_por_xpath(self, web):
        assert web.find(Locator.xpath("//h1")).text() == "Banco de pruebas"

    def test_por_texto(self, web):
        assert web.find(Locator.text("Buscar")).is_visible()

    def test_por_placeholder(self, web):
        assert web.find(Locator(Strategy.PLACEHOLDER, "Buscar algo")).is_visible()

    def test_por_etiqueta(self, web):
        assert web.find(Locator(Strategy.LABEL, "Correo electrónico")).is_visible()

    def test_por_rol(self, web):
        assert web.find(Locator.role("button", name="Buscar")).is_visible()

    def test_una_estrategia_no_soportada_falla_al_buscar(self, web):
        """Falla al localizar, no diez segundos después como 'no encontrado'."""
        with pytest.raises(UnsupportedStrategyError) as excinfo:
            web.find(Locator.automation_id("SearchBox"))

        assert excinfo.value.strategy is Strategy.AUTOMATION_ID


class TestConsultas:
    def test_exists_para_un_elemento_presente(self, web):
        assert web.find(TITULO).exists() is True

    def test_exists_para_un_elemento_ausente(self, web):
        assert web.find(AUSENTE).exists() is False

    def test_un_elemento_oculto_existe_pero_no_es_visible(self, web):
        oculto = web.find(OCULTO)

        assert oculto.exists() is True
        assert oculto.is_visible() is False

    def test_lee_un_atributo(self, web):
        enlace = web.find(Locator.test_id("enlace-destino"))

        assert enlace.attribute("title") == "ir"

    def test_un_atributo_ausente_es_none(self, web):
        assert web.find(TITULO).attribute("href") is None


class TestAcciones:
    def test_rellenar_y_pulsar(self, web):
        web.find(CAJA).fill("notepad")
        web.find(BOTON).click()

        assert web.find(RESULTADO).text() == "Resultados para: notepad"

    def test_fill_reemplaza_el_valor_anterior(self, web):
        caja = web.find(CAJA)
        caja.fill("primero")
        caja.fill("segundo")

        assert caja.value() == "segundo"

    def test_value_lee_lo_escrito_y_attribute_no(self, web):
        """El hallazgo de esta fase: escribir cambia la propiedad del DOM, no el atributo."""
        caja = web.find(CAJA)
        caja.fill("notepad")

        assert caja.value() == "notepad"
        assert caja.attribute("value") is None

    def test_value_sobre_algo_que_no_es_un_campo_se_rechaza(self, web):
        with pytest.raises(ElementError, match="no tiene un valor editable"):
            web.find(TITULO).value()


class TestAutoEspera:
    """Lo que hace que el framework sirva: nada de sleeps, sólo condiciones."""

    def test_una_accion_espera_a_que_el_elemento_aparezca(self, web):
        assert web.find(TARDIO).text() == "Ya llegué"

    def test_wait_for_visible_espera(self, web):
        web.find(TARDIO).wait_for(ElementState.VISIBLE)

    def test_wait_for_absent_espera_a_que_desaparezca(self, web):
        web.find(EFIMERO).wait_for(ElementState.ABSENT)

    def test_wait_for_hidden_se_cumple_con_un_elemento_oculto(self, web):
        web.find(OCULTO).wait_for(ElementState.HIDDEN, timeout=1)


class TestFallos:
    def test_un_elemento_ausente_da_element_not_found(self, web):
        with pytest.raises(ElementNotFoundError) as excinfo:
            web.find(AUSENTE).click(timeout=1)

        assert excinfo.value.locator is AUSENTE
        assert "algo que no está" in str(excinfo.value)

    def test_no_se_filtran_excepciones_de_playwright(self, web):
        """Si un TimeoutError de Playwright llegara al test, la abstracción tendría fugas."""
        with pytest.raises(ElementNotFoundError) as excinfo:
            web.find(AUSENTE).text(timeout=1)

        assert type(excinfo.value).__module__.startswith("automation_framework")

    def test_esperar_a_que_desaparezca_algo_permanente_da_timeout(self, web):
        with pytest.raises(WaitTimeoutError):
            web.find(TITULO).wait_for(ElementState.ABSENT, timeout=1)


class TestFindAll:
    def test_devuelve_un_handle_por_coincidencia(self, web):
        assert [fila.text() for fila in web.find_all(FILAS)] == ["uno", "dos", "tres"]

    def test_es_vacio_cuando_no_hay_coincidencias(self, web):
        assert web.find_all(AUSENTE) == []

    def test_cada_handle_apunta_a_su_propio_elemento(self, web):
        filas = web.find_all(FILAS)

        assert filas[1].text() == "dos"


class TestNavegacion:
    def test_goto_carga_otra_pagina(self, web, local_site):
        web.goto(f"{local_site}/destino.html")

        assert web.find(TITULO).text() == "Has llegado al destino"

    def test_pulsar_un_enlace_navega(self, web):
        web.find(Locator.test_id("enlace-destino")).click()

        assert web.find(TITULO).text() == "Has llegado al destino"


class TestCapturas:
    def test_screenshot_escribe_un_png(self, web, tmp_path):
        destino = web.screenshot(tmp_path / "captura.png")

        assert destino.exists()
        assert destino.read_bytes().startswith(b"\x89PNG")

    def test_crea_los_directorios_que_falten(self, web, tmp_path):
        assert web.screenshot(tmp_path / "a" / "b" / "captura.png").exists()
