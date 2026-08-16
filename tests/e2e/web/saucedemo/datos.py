"""Test data for the saucedemo suite.

The credentials live in `datos/usuarios.json` so that adding a case does not mean editing
Python. The dataclass is what makes a typo in the file fail on load, naming the file, instead
of surfacing as a `KeyError` halfway through a test.
"""

from dataclasses import dataclass
from pathlib import Path

from automation_framework.utils import data_path, load_mapping, merged


@dataclass(frozen=True)
class Usuario:
    """Una cuenta de saucedemo y lo que se espera de ella."""

    usuario: str
    clave: str
    puede_entrar: bool
    descripcion: str
    error_esperado: str | None = None

    @property
    def id(self) -> str:
        """Identificador legible para los informes de pytest."""
        return self.usuario


@dataclass(frozen=True)
class Cliente:
    """Los datos que pide el checkout."""

    nombre: str
    apellido: str
    codigo_postal: str


USUARIOS = load_mapping(data_path(Path(__file__), "datos", "usuarios.json"), Usuario)
"""Todas las cuentas conocidas, por nombre corto."""

CLIENTE_VALIDO = {"nombre": "Ada", "apellido": "Lovelace", "codigo_postal": "28001"}


def cliente(**cambios: str) -> Cliente:
    """Un cliente válido, con los campos que el test necesite cambiar.

    Así un test sobre el código postal que falta no tiene que deletrear además un nombre y un
    apellido que no le importan — y cuando el formulario gane un campo, se añade en un sitio.
    """
    return Cliente(**merged(CLIENTE_VALIDO, cambios))
