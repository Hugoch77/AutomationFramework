"""Tests for the page object base class.

`BasePage` is deliberately thin, so what is worth testing is the part that is easy to get
wrong: the difference between *asking* whether a screen is loaded (never raises, so a test can
choose between two screens) and *requiring* that it is (raises, naming the page rather than
whichever element the test happened to touch first).
"""

import pytest

from automation_framework.core.capabilities import Capabilities
from automation_framework.core.exceptions import PageNotLoadedError, UnsupportedStrategyError
from automation_framework.core.locator import Locator, Strategy
from automation_framework.pages import BasePage
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

CABECERA = Locator.test_id("cabecera", description="cabecera del catálogo")
BOTON = Locator.test_id("comprar", description="botón de comprar")
FILA = Locator.css("li.fila", description="filas del catálogo")
SOLO_CSS = Locator.css("h1", description="titular por CSS")


class PaginaCatalogo(BasePage):
    @property
    def marker(self):
        return CABECERA


class PaginaConNombrePropio(BasePage):
    @property
    def marker(self):
        return CABECERA

    @property
    def name(self):
        return "catálogo de productos"


class PaginaSoloCss(BasePage):
    """Una página cuyo marcador exige una estrategia que el engine puede no soportar."""

    @property
    def marker(self):
        return SOLO_CSS


class _EngineSinCss(FakeEngine):
    """Un engine que no resuelve CSS, como el de escritorio."""

    @property
    def capabilities(self):
        return Capabilities.of("sin-css", strategies=frozenset({Strategy.TEST_ID}))


@pytest.fixture
def engine():
    with FakeEngine() as instance:
        yield instance


@pytest.fixture
def engine_sin_css():
    with _EngineSinCss() as instance:
        yield instance


@pytest.fixture
def pagina(engine):
    return PaginaCatalogo(engine)


class TestContrato:
    def test_una_pagina_debe_declarar_su_marcador(self, engine):
        """Sin marcador no hay forma de responder "¿estoy en la pantalla correcta?"."""

        class SinMarcador(BasePage):
            pass

        with pytest.raises(TypeError):
            SinMarcador(engine)

    def test_el_nombre_por_defecto_es_el_de_la_clase(self, pagina):
        assert pagina.name == "PaginaCatalogo"

    def test_una_pagina_puede_dar_su_propio_nombre(self, engine):
        assert PaginaConNombrePropio(engine).name == "catálogo de productos"

    def test_expone_el_engine_para_lo_que_el_contrato_no_cubre(self, pagina, engine):
        assert pagina.engine is engine

    def test_el_repr_menciona_el_marcador(self, pagina):
        assert "cabecera del catálogo" in repr(pagina)


class TestBusqueda:
    def test_find_delega_en_el_engine(self, pagina, engine):
        engine.add(BOTON, text="Comprar")

        assert pagina.find(BOTON).text() == "Comprar"

    def test_find_all_delega_en_el_engine(self, pagina, engine):
        for texto in ("uno", "dos"):
            engine.add(FILA, text=texto)

        assert [fila.text() for fila in pagina.find_all(FILA)] == ["uno", "dos"]

    def test_una_estrategia_no_soportada_sigue_fallando_pronto(self, engine_sin_css):
        """La página delega en el engine: no debe tragarse sus guardas."""
        with pytest.raises(UnsupportedStrategyError):
            PaginaSoloCss(engine_sin_css).find(SOLO_CSS)


class TestIsLoaded:
    def test_es_verdadero_cuando_el_marcador_esta_visible(self, pagina, engine):
        engine.add(CABECERA, text="Products")

        assert pagina.is_loaded() is True

    def test_es_falso_cuando_el_marcador_no_esta(self, pagina):
        assert pagina.is_loaded() is False

    def test_es_falso_cuando_el_marcador_esta_pero_oculto(self, pagina, engine):
        engine.add(CABECERA, visible=False)

        assert pagina.is_loaded() is False

    def test_no_lanza_nunca(self, engine_sin_css):
        """Es una pregunta: una página que revienta al preguntarle "¿estás ahí?" no sirve
        para elegir entre dos pantallas posibles."""
        assert PaginaSoloCss(engine_sin_css).is_loaded() is False


class TestWaitUntilLoaded:
    def test_devuelve_la_propia_pagina_para_encadenar(self, pagina, engine):
        engine.add(CABECERA, text="Products")

        assert pagina.wait_until_loaded() is pagina

    def test_espera_a_un_marcador_que_tarda(self, pagina, engine):
        engine.add(CABECERA, text="Products", appear_after=3)

        pagina.wait_until_loaded()

    def test_falla_si_el_marcador_no_aparece(self, pagina):
        with pytest.raises(PageNotLoadedError):
            pagina.wait_until_loaded(timeout=0)

    def test_el_error_nombra_la_pagina_no_el_elemento(self, pagina):
        """ "No se encontró el botón" manda a leer el botón; el problema es que la app
        seguía en la pantalla anterior."""
        with pytest.raises(PageNotLoadedError) as excinfo:
            pagina.wait_until_loaded(timeout=0)

        assert "PaginaCatalogo" in str(excinfo.value)

    def test_el_error_incluye_el_marcador_que_falto(self, pagina):
        with pytest.raises(PageNotLoadedError, match="cabecera del catálogo"):
            pagina.wait_until_loaded(timeout=0)

    def test_el_error_dice_cuanto_se_espero(self, pagina):
        with pytest.raises(PageNotLoadedError) as excinfo:
            pagina.wait_until_loaded(timeout=0)

        assert excinfo.value.timeout == 0
