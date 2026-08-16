"""Tests for test-data loading.

The value of this module is not that it reads JSON — it is that a malformed data file fails
where the message can still name the file and the entry. A `KeyError` surfacing three fixtures
later, in a test that has nothing to do with the typo, is the failure mode being prevented.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from automation_framework.core.exceptions import ConfigurationError
from automation_framework.utils import (
    data_path,
    ids_for,
    load_json,
    load_mapping,
    load_records,
    merged,
)

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class Usuario:
    usuario: str
    clave: str
    activo: bool = True

    @property
    def id(self):
        return self.usuario


@pytest.fixture
def escribir(tmp_path):
    def _escribir(nombre, contenido):
        destino = tmp_path / nombre
        destino.write_text(
            contenido if isinstance(contenido, str) else json.dumps(contenido),
            encoding="utf-8",
        )
        return destino

    return _escribir


class TestLoadJson:
    def test_lee_un_fichero_valido(self, escribir):
        assert load_json(escribir("datos.json", {"clave": "valor"})) == {"clave": "valor"}

    def test_un_fichero_inexistente_falla_nombrando_la_ruta(self, tmp_path):
        """Sin la ruta, "no existe el fichero" manda a revisar fixtures a ciegas."""
        with pytest.raises(ConfigurationError, match=re.escape("no_existe.json")):
            load_json(tmp_path / "no_existe.json")

    def test_un_json_roto_falla_nombrando_la_ruta(self, escribir):
        with pytest.raises(ConfigurationError, match=re.escape("datos.json")):
            load_json(escribir("datos.json", "{esto no es json"))

    def test_lee_acentos(self, escribir):
        """Los datos de prueba de este proyecto van en español."""
        ruta = escribir("datos.json", {"descripcion": "código postal"})

        assert load_json(ruta)["descripcion"] == "código postal"


class TestLoadRecords:
    def test_construye_un_objeto_por_entrada(self, escribir):
        ruta = escribir(
            "usuarios.json",
            [{"usuario": "ada", "clave": "x"}, {"usuario": "grace", "clave": "y"}],
        )

        usuarios = load_records(ruta, Usuario)

        assert [usuario.usuario for usuario in usuarios] == ["ada", "grace"]

    def test_aplica_los_valores_por_defecto_de_la_factory(self, escribir):
        ruta = escribir("usuarios.json", [{"usuario": "ada", "clave": "x"}])

        assert load_records(ruta, Usuario)[0].activo is True

    def test_un_campo_desconocido_falla_al_cargar(self, escribir):
        """Aquí el mensaje puede nombrar el fichero; tres fixtures más tarde, ya no."""
        ruta = escribir("usuarios.json", [{"usuario": "ada", "clave": "x", "rol": "admin"}])

        with pytest.raises(ConfigurationError, match=re.escape("usuarios.json")):
            load_records(ruta, Usuario)

    def test_el_error_dice_que_entrada_falla(self, escribir):
        ruta = escribir(
            "usuarios.json",
            [{"usuario": "ada", "clave": "x"}, {"usuario": "grace"}],
        )

        with pytest.raises(ConfigurationError, match="entrada 1"):
            load_records(ruta, Usuario)

    def test_rechaza_un_fichero_que_no_es_una_lista(self, escribir):
        with pytest.raises(ConfigurationError, match="lista"):
            load_records(escribir("usuarios.json", {"usuario": "ada"}), Usuario)

    def test_rechaza_una_entrada_que_no_es_un_objeto(self, escribir):
        with pytest.raises(ConfigurationError, match="entrada 0"):
            load_records(escribir("usuarios.json", ["ada"]), Usuario)


class TestLoadMapping:
    def test_indexa_por_la_clave_del_fichero(self, escribir):
        ruta = escribir(
            "usuarios.json",
            {"admin": {"usuario": "ada", "clave": "x"}, "invitado": {"usuario": "g", "clave": "y"}},
        )

        usuarios = load_mapping(ruta, Usuario)

        assert usuarios["admin"].usuario == "ada"
        assert set(usuarios) == {"admin", "invitado"}

    def test_el_error_nombra_la_clave_que_falla(self, escribir):
        ruta = escribir("usuarios.json", {"admin": {"usuario": "ada"}})

        with pytest.raises(ConfigurationError, match="'admin'"):
            load_mapping(ruta, Usuario)

    def test_rechaza_un_fichero_que_no_es_un_objeto(self, escribir):
        with pytest.raises(ConfigurationError, match="objeto"):
            load_mapping(escribir("usuarios.json", [{"usuario": "ada", "clave": "x"}]), Usuario)

    def test_rechaza_una_entrada_que_no_es_un_objeto(self, escribir):
        with pytest.raises(ConfigurationError, match="'admin'"):
            load_mapping(escribir("usuarios.json", {"admin": "ada"}), Usuario)


class TestDataPath:
    def test_resuelve_relativo_al_modulo_que_lo_pide(self):
        """Para que una suite encuentre sus datos venga de donde venga la ejecución."""
        resuelto = data_path(Path(__file__), "datos", "usuarios.json")

        assert resuelto.parent.parent == Path(__file__).resolve().parent
        assert resuelto.name == "usuarios.json"


class TestMerged:
    def test_combina_de_izquierda_a_derecha(self):
        assert merged({"a": 1, "b": 2}, {"b": 3}) == {"a": 1, "b": 3}

    def test_no_modifica_el_original(self):
        base = {"a": 1}

        merged(base, {"a": 2})

        assert base == {"a": 1}

    def test_sin_cambios_devuelve_una_copia_equivalente(self):
        assert merged({"a": 1}) == {"a": 1}


class TestIdsFor:
    def test_usa_el_atributo_id_del_registro(self):
        """Sin esto, un fallo parametrizado se reporta como `test_login[usuario3]`."""
        registros = [Usuario("ada", "x"), Usuario("grace", "y")]

        assert ids_for(registros) == ["ada", "grace"]

    def test_acepta_otro_atributo(self):
        assert ids_for([Usuario("ada", "secreta")], "clave") == ["secreta"]

    def test_cae_al_propio_valor_cuando_no_hay_atributo(self):
        assert ids_for(["uno", "dos"]) == ["uno", "dos"]
