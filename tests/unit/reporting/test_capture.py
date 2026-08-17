"""Tests for log capture.

El framework ya etiquetaba cada línea con el test que la produjo; lo que faltaba era guardar
una copia para adjuntarla. Se prueba a través de la cadena real de structlog —no de un doble—
porque el punto delicado es justamente que el `logger_factory` se integre con los procesadores
que inyectan el contexto.
"""

import io

import pytest

from automation_framework.core.log import bound_context, configure_logging, get_logger
from automation_framework.reporting import LogCapture, TeeLogger, capturing_logger_factory

pytestmark = pytest.mark.unit


@pytest.fixture
def capture():
    return LogCapture()


@pytest.fixture
def logging_configurado(capture):
    """structlog cableado a la captura, y devuelto a un estado limpio al terminar."""
    configure_logging(level="INFO", logger_factory=capturing_logger_factory(capture))
    yield capture
    configure_logging(level="INFO")


class TestLogCapture:
    def test_empieza_inactiva(self, capture):
        """Sin esto, los logs de la fase de arranque de la sesión entrarían en el primer test."""
        capture.add("una línea")

        assert capture.text() == ""

    def test_dice_si_esta_capturando(self, capture):
        assert capture.active is False

        capture.start()
        assert capture.active is True

        capture.stop()
        assert capture.active is False

    def test_guarda_lo_que_llega_tras_arrancar(self, capture):
        capture.start()
        capture.add("una línea")

        assert capture.text() == "una línea"

    def test_start_descarta_lo_del_test_anterior(self, capture):
        capture.start()
        capture.add("del test anterior")

        capture.start()
        capture.add("del test actual")

        assert capture.text() == "del test actual"

    def test_stop_deja_de_guardar_pero_conserva_lo_ya_guardado(self, capture):
        capture.start()
        capture.add("durante el test")
        capture.stop()
        capture.add("del teardown de otra cosa")

        assert capture.text() == "durante el test"

    def test_quita_los_colores_de_la_consola(self, capture):
        """En un fichero adjunto los códigos ANSI se cuelan entre cada palabra."""
        capture.start()
        capture.add("\x1b[32minfo\x1b[0m navegando")

        assert capture.text() == "info navegando"

    def test_no_toca_los_corchetes_normales(self, capture):
        """Quitar color no puede comerse texto que da la casualidad de parecerse."""
        capture.start()
        capture.add("elemento lista[0] con [1;2m entre corchetes")

        assert capture.text() == "elemento lista[0] con [1;2m entre corchetes"

    def test_cuenta_las_lineas(self, capture):
        capture.start()
        capture.add("una")
        capture.add("dos")

        assert len(capture) == 2


class TestTeeLogger:
    def test_escribe_en_el_flujo(self, capture):
        """Duplicar no puede significar dejar de imprimir: la consola de CI sigue importando."""
        flujo = io.StringIO()

        TeeLogger(capture, flujo).msg("hola")

        assert "hola" in flujo.getvalue()

    def test_guarda_una_copia(self, capture):
        capture.start()

        TeeLogger(capture, io.StringIO()).msg("hola")

        assert capture.text() == "hola"

    @pytest.mark.parametrize("nivel", ["info", "warning", "error", "debug", "critical"])
    def test_todos_los_niveles_escriben(self, capture, nivel):
        """structlog llama al método del nivel; el nivel ya viene renderizado en la línea."""
        capture.start()

        getattr(TeeLogger(capture, io.StringIO()), nivel)("mensaje")

        assert capture.text() == "mensaje"


class TestIntegracionConStructlog:
    def test_captura_lo_que_se_registra_de_verdad(self, logging_configurado):
        logging_configurado.start()

        get_logger(__name__).info("buscando", termino="notepad")

        assert "buscando" in logging_configurado.text()

    def test_las_lineas_conservan_el_contexto_del_test(self, logging_configurado):
        """Lo que hace útil el adjunto: cada línea dice a qué test pertenece."""
        logging_configurado.start()

        with bound_context(test_id="test_busqueda"):
            get_logger(__name__).info("dentro del test")

        assert "test_busqueda" in logging_configurado.text()

    def test_respeta_el_nivel_configurado(self, capture):
        configure_logging(level="WARNING", logger_factory=capturing_logger_factory(capture))
        capture.start()

        get_logger(__name__).info("no debería aparecer")
        get_logger(__name__).warning("sí debería")

        assert "no debería aparecer" not in capture.text()
        assert "sí debería" in capture.text()

    def test_los_datos_estructurados_llegan_al_adjunto(self, logging_configurado):
        logging_configurado.start()

        get_logger(__name__).info("navegando", url="https://ejemplo.test")

        assert "ejemplo.test" in logging_configurado.text()
