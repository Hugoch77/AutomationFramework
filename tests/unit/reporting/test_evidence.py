"""Tests for evidence collection.

Lo que se protege aquí es una propiedad incómoda pero esencial: **recoger evidencia no puede
fallar nunca**. Corre desde un teardown, así que una excepción suya sustituiría el fallo real
del test por otro sobre capturas de pantalla, y quien lea el informe perdería la causa.
"""

import pytest

from automation_framework.core.capabilities import Capabilities
from automation_framework.core.locator import Locator, Strategy
from automation_framework.reporting import Evidence, collect_evidence, describe
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

RAIZ = Locator.test_id("raiz", description="contenedor")


class _EngineSinNada(FakeEngine):
    """Un engine que no puede producir evidencia: ni captura ni árbol."""

    @property
    def capabilities(self):
        return Capabilities.of("pelado", strategies=frozenset({Strategy.TEST_ID}))


class _EngineQueRevienta(FakeEngine):
    """Un engine cuyas capturas fallan, como una sesión de navegador ya muerta."""

    def _screenshot(self, path):
        raise OSError("el navegador ya no está")

    def _dump_tree(self):
        raise RuntimeError("contexto destruido")


class _EngineConTraza(FakeEngine):
    def save_trace(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"traza-falsa")
        return path


class _EngineConTrazaRota(FakeEngine):
    def save_trace(self, path):
        raise OSError("disco lleno")


@pytest.fixture
def engine():
    with FakeEngine() as instance:
        instance.add(RAIZ, text="Hola")
        yield instance


class TestRecoleccion:
    def test_recoge_captura_y_arbol(self, engine, tmp_path):
        recogida = collect_evidence(engine, tmp_path)

        nombres = [item.path.name for item in recogida]
        assert "captura.png" in nombres
        assert "arbol.html" in nombres

    def test_crea_la_carpeta_de_destino(self, engine, tmp_path):
        destino = tmp_path / "no" / "existe"

        collect_evidence(engine, destino)

        assert destino.exists()

    def test_los_ficheros_se_escriben_de_verdad(self, engine, tmp_path):
        """Una entrada en la lista que no corresponda a un fichero real sería peor que nada."""
        for item in collect_evidence(engine, tmp_path):
            assert item.path.exists(), item.name

    def test_el_arbol_contiene_el_estado_de_la_aplicacion(self, engine, tmp_path):
        recogida = collect_evidence(engine, tmp_path)

        arbol = next(item for item in recogida if item.path.name == "arbol.html")
        assert "contenedor" in arbol.path.read_text(encoding="utf-8")

    def test_adjunta_los_logs_cuando_se_le_pasan(self, engine, tmp_path):
        recogida = collect_evidence(engine, tmp_path, logs="pasó esto\ny luego esto")

        registro = next(item for item in recogida if item.path.name == "registro.log")
        assert "y luego esto" in registro.path.read_text(encoding="utf-8")

    def test_sin_logs_no_hay_fichero_de_registro(self, engine, tmp_path):
        """Un adjunto vacío en el informe es ruido que hay que abrir para descubrir que no dice
        nada."""
        recogida = collect_evidence(engine, tmp_path, logs="")

        assert all(item.path.name != "registro.log" for item in recogida)


class TestCapabilities:
    def test_no_pide_lo_que_el_engine_no_declara(self, tmp_path):
        with _EngineSinNada() as engine:
            assert collect_evidence(engine, tmp_path) == []

    def test_recoge_la_traza_de_quien_la_ofrece(self, tmp_path):
        with _EngineConTraza() as engine:
            nombres = [item.path.name for item in collect_evidence(engine, tmp_path)]

        assert "traza.zip" in nombres

    def test_un_engine_sin_traza_no_es_un_problema(self, engine, tmp_path):
        """`save_trace` no está en el contrato: sólo lo tienen los engines que graban."""
        nombres = [item.path.name for item in collect_evidence(engine, tmp_path)]

        assert "traza.zip" not in nombres


class TestNuncaLanza:
    """La propiedad central: la recolección se traga sus propios fallos.

    Si reventara, el informe hablaría de la captura de pantalla en lugar del test que falló.
    """

    def test_sobrevive_a_un_engine_que_revienta(self, tmp_path):
        with _EngineQueRevienta() as engine:
            assert collect_evidence(engine, tmp_path) == []

    def test_sobrevive_a_una_traza_rota(self, tmp_path):
        with _EngineConTrazaRota() as engine:
            recogida = collect_evidence(engine, tmp_path)

        assert all(item.path.name != "traza.zip" for item in recogida)

    def test_lo_que_si_funciona_se_recoge_igual(self, tmp_path):
        """Un fallo aislado no puede llevarse por delante el resto de la evidencia."""
        with _EngineConTrazaRota() as engine:
            engine.add(RAIZ, text="Hola")
            recogida = collect_evidence(engine, tmp_path)

        assert [item.path.name for item in recogida] == ["captura.png", "arbol.html"]


class TestDescribe:
    def test_enumera_lo_recogido(self, engine, tmp_path):
        assert "captura.png" in describe(collect_evidence(engine, tmp_path))

    def test_lo_dice_cuando_no_hay_nada(self):
        assert describe([]) == "sin evidencia"

    def test_usa_el_nombre_del_fichero_no_la_ruta_entera(self, tmp_path):
        evidencia = [Evidence("Captura", tmp_path / "a" / "b" / "captura.png", "image/png")]

        assert describe(evidencia) == "captura.png"
