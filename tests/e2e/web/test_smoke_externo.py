"""Smoke contra un sitio público real.

El resto de la suite web corre contra páginas locales para que el CI no dependa de terceros.
Estos dos tests existen para lo que aquellas no pueden dar: HTML real, latencia real,
redirecciones y carga asíncrona de verdad.

Marcados como `external`. Si fallan, lo primero que hay que descartar es que el problema
esté en saucedemo.com y no en este código.
"""

import pytest

from automation_framework.core.locator import Locator

pytestmark = [
    pytest.mark.web,
    pytest.mark.external,
    pytest.mark.slow,
    # saucedemo publica sus hooks como data-test, no como data-testid.
    pytest.mark.af_config(test_id_attribute="data-test"),
]

SITIO = "https://www.saucedemo.com"

USUARIO = Locator.test_id("username", description="campo de usuario")
CLAVE = Locator.test_id("password", description="campo de contraseña")
ENTRAR = Locator.test_id("login-button", description="botón de entrar")
TITULO_CATALOGO = Locator.css(".title", description="título del catálogo")
ARTICULOS = Locator.test_id("inventory-item", description="artículos del catálogo")
ERROR = Locator.test_id("error", description="mensaje de error de login")


@pytest.fixture
def sitio(engine):
    engine.goto(SITIO)
    return engine


class TestLogin:
    def test_un_login_valido_lleva_al_catalogo(self, sitio):
        sitio.find(USUARIO).fill("standard_user")
        sitio.find(CLAVE).fill("secret_sauce")
        sitio.find(ENTRAR).click()

        assert sitio.find(TITULO_CATALOGO).text() == "Products"
        assert len(sitio.find_all(ARTICULOS)) == 6

    def test_un_login_invalido_muestra_error(self, sitio):
        sitio.find(USUARIO).fill("usuario_inexistente")
        sitio.find(CLAVE).fill("clave_incorrecta")
        sitio.find(ENTRAR).click()

        assert "do not match" in sitio.find(ERROR).text()
