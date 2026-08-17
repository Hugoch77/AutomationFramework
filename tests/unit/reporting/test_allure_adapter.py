"""Tests for the Allure adapter.

Este es el único módulo del framework que sabe que Allure existe, así que lo que se prueba es
que **esa dependencia esté bien contenida**: si el reporter no está instalado, o si falla al
adjuntar, la ejecución sigue y la evidencia ya está en disco de todas formas.
"""

import pytest

from automation_framework.reporting import Evidence, allure_adapter

pytestmark = pytest.mark.unit


@pytest.fixture
def evidencia(tmp_path):
    captura = tmp_path / "captura.png"
    captura.write_bytes(b"\x89PNG falsa")
    return [Evidence("Captura de pantalla", captura, "image/png")]


@pytest.fixture
def sin_allure(monkeypatch):
    """Simula una instalación sin allure-pytest."""
    monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", False)


class TestDisponibilidad:
    def test_informa_de_si_puede_publicar(self):
        assert allure_adapter.is_available() is allure_adapter.ALLURE_AVAILABLE

    def test_sin_allure_no_adjunta_nada_y_no_falla(self, sin_allure, evidencia):
        """Un reporter ausente degrada el informe; no puede romper la ejecución."""
        assert allure_adapter.attach_evidence(evidencia) == 0

    def test_sin_allure_el_texto_tampoco_falla(self, sin_allure):
        assert allure_adapter.attach_text("Registro", "contenido") is False


class TestAttachEvidence:
    def test_nunca_lanza_aunque_el_fichero_no_exista(self, tmp_path):
        """Corre desde un teardown: una excepción aquí taparía el fallo real del test."""
        fantasma = [Evidence("Inexistente", tmp_path / "no_existe.png", "image/png")]

        allure_adapter.attach_evidence(fantasma)

    def test_una_lista_vacia_no_adjunta_nada(self):
        assert allure_adapter.attach_evidence([]) == 0

    def test_nunca_lanza_si_el_reporter_revienta(self, monkeypatch, evidencia):
        class _AllureRoto:
            class attach:  # noqa: N801
                @staticmethod
                def file(*args, **kwargs):
                    raise RuntimeError("el reporter está roto")

        monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", True)
        monkeypatch.setattr(allure_adapter, "_allure", _AllureRoto)

        assert allure_adapter.attach_evidence(evidencia) == 0

    def test_cuenta_los_adjuntos_que_si_salen(self, monkeypatch, evidencia):
        adjuntados = []

        class _AllureQueApunta:
            class attach:  # noqa: N801
                @staticmethod
                def file(source, name, attachment_type, extension):
                    adjuntados.append((name, attachment_type, extension))

        monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", True)
        monkeypatch.setattr(allure_adapter, "_allure", _AllureQueApunta)

        assert allure_adapter.attach_evidence(evidencia) == 1
        assert adjuntados == [("Captura de pantalla", "image/png", "png")]


class TestAttachText:
    def test_un_texto_vacio_no_se_adjunta(self, monkeypatch):
        """Un adjunto vacío obliga a abrirlo para descubrir que no dice nada."""
        monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", True)

        assert allure_adapter.attach_text("Registro", "") is False

    def test_adjunta_un_texto_cuando_hay_reporter(self, monkeypatch):
        adjuntados = []

        class _AllureQueApunta:
            @staticmethod
            def attach(content, name, attachment_type):
                adjuntados.append((content, name, attachment_type))

        monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", True)
        monkeypatch.setattr(allure_adapter, "_allure", _AllureQueApunta)

        assert allure_adapter.attach_text("Registro", "una línea") is True
        assert adjuntados == [("una línea", "Registro", "text/plain")]

    def test_nunca_lanza_si_el_reporter_revienta(self, monkeypatch):
        class _AllureRoto:
            @staticmethod
            def attach(*args, **kwargs):
                raise RuntimeError("el reporter está roto")

        monkeypatch.setattr(allure_adapter, "ALLURE_AVAILABLE", True)
        monkeypatch.setattr(allure_adapter, "_allure", _AllureRoto)

        assert allure_adapter.attach_text("Registro", "una línea") is False


class TestEnvironment:
    def test_escribe_el_fichero_de_entorno(self, tmp_path):
        allure_adapter.describe_environment({"browser": "chromium"}, tmp_path)

        assert (tmp_path / "environment.properties").read_text(encoding="utf-8") == (
            "browser=chromium"
        )

    def test_ordena_las_claves(self, tmp_path):
        """Un orden estable hace comparables dos informes seguidos."""
        allure_adapter.describe_environment({"z": "1", "a": "2"}, tmp_path)

        contenido = (tmp_path / "environment.properties").read_text(encoding="utf-8")
        assert contenido.splitlines() == ["a=2", "z=1"]

    def test_crea_el_directorio_si_falta(self, tmp_path):
        destino = tmp_path / "allure-results"

        allure_adapter.describe_environment({"browser": "chromium"}, destino)

        assert (destino / "environment.properties").exists()

    def test_sin_valores_no_escribe_nada(self, tmp_path):
        assert allure_adapter.describe_environment({}, tmp_path) is False
        assert not (tmp_path / "environment.properties").exists()

    def test_un_destino_imposible_no_rompe_la_ejecucion(self, tmp_path):
        """El entorno es un extra del informe; no puede tumbar la sesión de tests."""
        ocupado = tmp_path / "fichero"
        ocupado.write_text("no soy un directorio", encoding="utf-8")

        assert allure_adapter.describe_environment({"browser": "chromium"}, ocupado) is False
