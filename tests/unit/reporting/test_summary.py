"""Tests for the CI job summary.

Esta es la parte del reporting que se lee **sin descargar nada**, así que lo que importa es que
diga la verdad en el peor momento: cuando la ejecución fue mal. Y que no reviente por su cuenta,
porque un resumen roto no puede convertir en rojo una build que ya tenía sus propios problemas.
"""

import pytest

from automation_framework.reporting.summary import (
    MAX_FAILURES_SHOWN,
    main,
    parse,
    render,
)

pytestmark = pytest.mark.unit

VERDE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="1" tests="4" time="12.5">
    <testcase classname="tests.test_a" name="test_uno" time="1.0"/>
    <testcase classname="tests.test_a" name="test_dos" time="1.0"/>
    <testcase classname="tests.test_a" name="test_tres" time="1.0"/>
    <testcase classname="tests.test_a" name="test_omitido" time="0.0"><skipped/></testcase>
  </testsuite>
</testsuites>
"""

ROJO = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="1" failures="1" skipped="0" tests="3" time="8.25">
    <testcase classname="tests.test_a" name="test_bien" time="1.0"/>
    <testcase classname="tests.test_a" name="test_mal" time="1.0">
      <failure message="assert 3 == 6&#10;detalle largo que sobra">AssertionError</failure>
    </testcase>
    <testcase classname="tests.test_b" name="test_roto" time="1.0">
      <error message="fixture no encontrada">Error</error>
    </testcase>
  </testsuite>
</testsuites>
"""


@pytest.fixture
def junit(tmp_path):
    def _escribir(contenido, nombre="junit.xml"):
        destino = tmp_path / nombre
        destino.write_text(contenido, encoding="utf-8")
        return destino

    return _escribir


class TestParse:
    def test_cuenta_una_ejecucion_verde(self, junit):
        resumen = parse(junit(VERDE))

        assert (resumen.total, resumen.failed, resumen.skipped) == (4, 0, 1)
        assert resumen.passed == 3
        assert resumen.ok is True

    def test_cuenta_una_ejecucion_roja(self, junit):
        resumen = parse(junit(ROJO))

        assert (resumen.failed, resumen.errors) == (1, 1)
        assert resumen.passed == 1
        assert resumen.ok is False

    def test_un_error_cuenta_como_fallo_para_el_veredicto(self, junit):
        """Un error de fixture no es "menos grave" que un assert: la build no está sana."""
        resumen = parse(junit(ROJO))

        assert resumen.ok is False

    def test_recoge_la_duracion(self, junit):
        assert parse(junit(VERDE)).duration == pytest.approx(12.5)

    def test_recoge_los_tests_fallidos(self, junit):
        fallos = parse(junit(ROJO)).failures

        assert [fallo.name for fallo in fallos] == ["test_mal", "test_roto"]

    def test_se_queda_con_la_primera_linea_del_mensaje(self, junit):
        """El mensaje completo trae el assert desplegado y ocupa media pantalla."""
        fallo = parse(junit(ROJO)).failures[0]

        assert fallo.message == "assert 3 == 6"

    def test_acepta_un_testsuite_sin_envoltorio(self, junit):
        suelto = VERDE.replace("<testsuites>", "").replace("</testsuites>", "")

        assert parse(junit(suelto)).total == 4


class TestRender:
    def test_una_ejecucion_verde_se_marca_como_tal(self, junit):
        salida = render(parse(junit(VERDE)))

        assert salida.startswith("## ✅")

    def test_una_ejecucion_roja_se_marca_como_tal(self, junit):
        assert render(parse(junit(ROJO))).startswith("## ❌")

    def test_incluye_la_tabla_de_conteos(self, junit):
        salida = render(parse(junit(VERDE)))

        assert "| Total | Pasados | Fallidos | Errores | Omitidos | Duración |" in salida
        assert "| 4 | 3 | 0 | 0 | 1 | 12.5s |" in salida

    def test_lista_los_fallos_con_su_motivo(self, junit):
        salida = render(parse(junit(ROJO)))

        assert "`tests.test_a::test_mal` — assert 3 == 6" in salida

    def test_una_ejecucion_verde_no_lista_fallos(self, junit):
        assert "Tests fallidos" not in render(parse(junit(VERDE)))

    def test_apunta_a_donde_esta_la_evidencia(self, junit):
        """El resumen se lee en el PR; la evidencia hay que saber dónde buscarla."""
        assert "artifact" in render(parse(junit(ROJO)))

    def test_acepta_un_titulo_propio(self, junit):
        """Cada job publica el suyo: sin título propio, dos resúmenes serían indistinguibles."""
        assert "Suite web" in render(parse(junit(VERDE)), title="Suite web")

    def test_recorta_una_lista_de_fallos_demasiado_larga(self, tmp_path):
        casos = "".join(
            f'<testcase classname="t" name="test_{i}">'
            f'<failure message="falló">x</failure></testcase>'
            for i in range(MAX_FAILURES_SHOWN + 5)
        )
        destino = tmp_path / "junit.xml"
        destino.write_text(
            f'<testsuite tests="{MAX_FAILURES_SHOWN + 5}" failures="{MAX_FAILURES_SHOWN + 5}" '
            f'errors="0" skipped="0" time="1.0">{casos}</testsuite>',
            encoding="utf-8",
        )

        salida = render(parse(destino))

        assert "y 5 más" in salida
        assert salida.count("- `t::test_") == MAX_FAILURES_SHOWN


class TestMain:
    def test_escribe_el_resumen(self, junit, capsys):
        main([str(junit(VERDE))])

        assert "✅" in capsys.readouterr().out

    def test_un_fichero_que_falta_no_rompe_la_build(self, tmp_path, capsys):
        """Un resumen que no se puede generar es un problema cosmético. Salir con error
        pondría en rojo una build por el informe, tapando lo que dijeran los tests."""
        assert main([str(tmp_path / "no_existe.xml")]) == 0
        assert "No se pudo generar el resumen" in capsys.readouterr().out

    def test_un_xml_roto_no_rompe_la_build(self, junit, capsys):
        assert main([str(junit("{no soy xml"))]) == 0
        assert "No se pudo generar el resumen" in capsys.readouterr().out

    def test_sin_argumentos_explica_como_usarlo(self, capsys):
        assert main([]) == 0
        assert "Uso:" in capsys.readouterr().out

    def test_acepta_el_titulo_como_segundo_argumento(self, junit, capsys):
        main([str(junit(VERDE)), "Suite web"])

        assert "Suite web" in capsys.readouterr().out

    def test_sobrevive_a_una_consola_que_no_habla_utf8(self, junit, monkeypatch, tmp_path):
        """Trampa ya pisada: la consola de Windows es cp1252 y no sabe escribir los iconos
        de estado. En un runner de GitHub no se ve, pero revienta en la máquina del usuario,
        que es donde menos gracia hace que la herramienta explote en vez de informar."""
        destino = tmp_path / "salida.txt"
        with destino.open("w", encoding="cp1252") as consola:
            monkeypatch.setattr("sys.stdout", consola)
            codigo = main([str(junit(ROJO))])

        assert codigo == 0
        assert "Tests fallidos" in destino.read_text(encoding="utf-8")

    def test_un_fallo_inesperado_tampoco_rompe_la_build(self, junit, monkeypatch, capsys):
        """La promesa es que este comando nunca tumba una ejecución, pase lo que pase."""
        monkeypatch.setattr(
            "automation_framework.reporting.summary.render",
            lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("algo raro")),
        )

        assert main([str(junit(VERDE))]) == 0
        assert "No se pudo generar el resumen" in capsys.readouterr().out
