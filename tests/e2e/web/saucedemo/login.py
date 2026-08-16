"""The login screen."""

from automation_framework.core.locator import Locator
from automation_framework.pages import BasePage


class PaginaLogin(BasePage):
    """Pantalla de entrada de saucedemo."""

    RUTA = "/"

    USUARIO = Locator.test_id("username", description="campo de usuario")
    CLAVE = Locator.test_id("password", description="campo de contraseña")
    ENTRAR = Locator.test_id("login-button", description="botón de entrar")
    ERROR = Locator.test_id("error", description="mensaje de error del login")

    @property
    def marker(self):
        return self.ENTRAR

    @property
    def name(self):
        return "login"

    def abrir(self):
        """Navega a la pantalla de login y espera a que esté lista."""
        self.engine.goto(self.RUTA)
        return self.wait_until_loaded()

    def entrar_como(self, usuario: str, clave: str) -> None:
        """Rellena las credenciales y envía el formulario.

        No devuelve la página siguiente a propósito: un login inválido se queda aquí, y una
        firma que prometiera el catálogo estaría mintiendo la mitad de las veces. Cada test
        declara qué pantalla espera.
        """
        self.find(self.USUARIO).fill(usuario)
        self.find(self.CLAVE).fill(clave)
        self.find(self.ENTRAR).click()

    @property
    def error(self):
        """El mensaje de error, para que el test lo compruebe con sus propias assertions."""
        return self.find(self.ERROR)
