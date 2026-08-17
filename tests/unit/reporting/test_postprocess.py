"""Tests for the report clean-up.

El riesgo real de esta pieza no es que borre de más: es que un día deje de casar con el HTML
que genera Allure y **siga diciendo que todo va bien**. Por eso hay tanto tests de que quita el
rastreador como de que avisa cuando no ha podido.
"""

import pytest

from automation_framework.reporting.postprocess import (
    clean_file,
    has_trackers,
    main,
    strip_analytics,
)

pytestmark = pytest.mark.unit

# Reproduce la forma real del informe generado por Allure 2.32.
CON_TELEMETRIA = """<html><head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-123"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('config', 'G-123');
    </script>
    <title>Allure Report</title>
</head><body><div id="alert"></div></body></html>"""


class TestStripAnalytics:
    def test_quita_el_script_del_rastreador(self):
        assert "googletagmanager" not in strip_analytics(CON_TELEMETRIA)

    def test_quita_el_bloque_datalayer(self):
        assert "dataLayer" not in strip_analytics(CON_TELEMETRIA)

    def test_conserva_el_resto_del_informe(self):
        """Limpiar no puede llevarse por delante el informe, que es lo que se va a leer."""
        limpio = strip_analytics(CON_TELEMETRIA)

        assert "<title>Allure Report</title>" in limpio
        assert '<div id="alert"></div>' in limpio

    def test_es_idempotente(self):
        una = strip_analytics(CON_TELEMETRIA)

        assert strip_analytics(una) == una

    def test_un_informe_ya_limpio_se_queda_igual(self):
        limpio = "<html><body>informe</body></html>"

        assert strip_analytics(limpio) == limpio

    def test_no_toca_otros_scripts(self):
        """El informe es casi todo JavaScript: borrar de más lo dejaría en blanco."""
        html = '<script src="data:text/javascript;base64,QUJD"></script>'

        assert strip_analytics(html) == html


class TestHasTrackers:
    def test_detecta_el_rastreador(self):
        assert has_trackers(CON_TELEMETRIA) is True

    def test_no_ve_rastreadores_donde_no_los_hay(self):
        assert has_trackers("<html>limpio</html>") is False

    def test_detecta_tambien_google_analytics_clasico(self):
        assert has_trackers('<script src="https://www.google-analytics.com/analytics.js">') is True


class TestCleanFile:
    def test_limpia_el_fichero_en_disco(self, tmp_path):
        informe = tmp_path / "index.html"
        informe.write_text(CON_TELEMETRIA, encoding="utf-8")

        assert clean_file(informe) is True
        assert "googletagmanager" not in informe.read_text(encoding="utf-8")

    def test_informa_de_que_no_pudo_limpiarlo(self, tmp_path):
        """Si Allure cambia el marcado, esto tiene que notarse."""
        informe = tmp_path / "index.html"
        informe.write_text(
            '<img src="https://www.google-analytics.com/pixel.gif">', encoding="utf-8"
        )

        assert clean_file(informe) is False


class TestMain:
    def test_avisa_cuando_ha_limpiado(self, tmp_path, capsys):
        informe = tmp_path / "index.html"
        informe.write_text(CON_TELEMETRIA, encoding="utf-8")

        assert main([str(informe)]) == 0
        assert "Telemetría eliminada" in capsys.readouterr().out

    def test_avisa_en_voz_alta_cuando_queda_un_rastreador(self, tmp_path, capsys):
        informe = tmp_path / "index.html"
        informe.write_text('<img src="https://www.google-analytics.com/p.gif">', encoding="utf-8")

        main([str(informe)])

        assert "AVISO" in capsys.readouterr().out

    def test_un_fichero_que_falta_no_rompe_la_build(self, tmp_path, capsys):
        assert main([str(tmp_path / "no_existe.html")]) == 0
        assert "AVISO" in capsys.readouterr().out

    def test_sin_argumentos_explica_como_usarlo(self, capsys):
        assert main([]) == 0
        assert "Uso:" in capsys.readouterr().out
