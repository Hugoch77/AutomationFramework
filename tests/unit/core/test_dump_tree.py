"""Tests for the element tree dump.

`Feature.ELEMENT_TREE_DUMP` existía desde la Fase 1 sin ninguna operación detrás: una
capability que nadie podía usar. Lo que se prueba aquí es que la operación respeta las mismas
guardas que el resto del contrato, porque un engine de escritorio sí puede no soportarla.
"""

import pytest

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.exceptions import EngineNotStartedError, UnsupportedOperationError
from automation_framework.core.locator import Locator, Strategy
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

RAIZ = Locator.test_id("raiz", description="contenedor")
HIJO = Locator.css(".hijo", description="elemento anidado")


class _EngineSinVolcado(FakeEngine):
    """Un engine que no sabe volcar su árbol."""

    @property
    def capabilities(self):
        return Capabilities.of("sin-volcado", strategies=frozenset({Strategy.TEST_ID}))


@pytest.fixture
def engine():
    with FakeEngine() as instance:
        yield instance


class TestGuardas:
    def test_falla_si_el_engine_no_esta_arrancado(self):
        with pytest.raises(EngineNotStartedError) as excinfo:
            FakeEngine().dump_tree()

        assert excinfo.value.operation == "dump_tree"

    def test_falla_si_el_engine_no_declara_la_capability(self):
        """Igual que screenshot: una operación no soportada se dice, no se devuelve vacía.

        Devolver "" sería peor que fallar: la evidencia parecería recogida y estaría vacía.
        """
        with _EngineSinVolcado() as engine, pytest.raises(UnsupportedOperationError):
            engine.dump_tree()

    def test_el_engine_de_referencia_declara_la_capability(self, engine):
        assert engine.has_feature(Feature.ELEMENT_TREE_DUMP) is True


class TestContenido:
    def test_incluye_los_elementos_de_la_aplicacion(self, engine):
        engine.add(RAIZ, text="Hola")

        assert "contenedor" in engine.dump_tree()

    def test_distingue_lo_visible_de_lo_oculto(self, engine):
        """La diferencia entre "no está" y "está pero no se ve" es justo lo que una captura
        de pantalla no puede contar."""
        engine.add(RAIZ, text="Hola", visible=False)

        assert "oculto" in engine.dump_tree()

    def test_anida_los_descendientes(self, engine):
        raiz = engine.add(RAIZ, text="Hola")
        raiz.add_child(HIJO, text="dentro")

        volcado = engine.dump_tree()

        assert "elemento anidado" in volcado
        assert volcado.splitlines()[1].startswith("  ")

    def test_una_aplicacion_vacia_da_un_volcado_vacio(self, engine):
        assert engine.dump_tree() == ""
