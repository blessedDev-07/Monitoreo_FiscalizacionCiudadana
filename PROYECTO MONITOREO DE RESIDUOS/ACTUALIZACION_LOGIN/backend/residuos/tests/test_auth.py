import pytest

from residuos.models import Usuario


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user("carlos", password="clave123", rol=Usuario.Rol.OPERADOR)


def test_login_correcto_devuelve_token(cliente_anonimo, usuario):
    r = cliente_anonimo.post("/api/login/", {"username": "carlos", "password": "clave123"}, format="json")
    assert r.status_code == 200
    assert r.json()["token"] and r.json()["usuario"]["rol"] == "OPERADOR"


def test_login_incorrecto_devuelve_401(cliente_anonimo, usuario):
    r = cliente_anonimo.post("/api/login/", {"username": "carlos", "password": "mal"}, format="json")
    assert r.status_code == 401


def test_api_sin_token_devuelve_401(cliente_anonimo):
    assert cliente_anonimo.get("/api/incidencias/").status_code == 401


def test_api_con_token_funciona(cliente_anonimo, usuario):
    token = cliente_anonimo.post("/api/login/", {"username": "carlos", "password": "clave123"},
                                 format="json").json()["token"]
    cliente_anonimo.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert cliente_anonimo.get("/api/incidencias/").status_code == 200


def test_logout_invalida_token(cliente_anonimo, usuario):
    token = cliente_anonimo.post("/api/login/", {"username": "carlos", "password": "clave123"},
                                 format="json").json()["token"]
    cliente_anonimo.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert cliente_anonimo.post("/api/logout/").status_code == 204
    assert cliente_anonimo.get("/api/incidencias/").status_code == 401
