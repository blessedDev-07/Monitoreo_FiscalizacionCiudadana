import pytest
from rest_framework.test import APIClient

from residuos.models import Camion, Horario, Ruta, Sector, Usuario


@pytest.fixture
def cliente(db):
    """Cliente ya autenticado (la API exige login)."""
    c = APIClient()
    c.force_authenticate(user=Usuario.objects.create_user("tester", password="x"))
    return c


@pytest.fixture
def cliente_anonimo():
    return APIClient()


@pytest.fixture
def sector(db):
    return Sector.objects.create(nombre="La Esperanza")


@pytest.fixture
def operador(db):
    return Usuario.objects.create_user("op1", password="x", rol=Usuario.Rol.OPERADOR)


@pytest.fixture
def camion(db, operador):
    return Camion.objects.create(codigo="AM-01", placa="ABC-123", operador=operador)


@pytest.fixture
def ruta(db, sector, camion):
    return Ruta.objects.create(nombre="Ruta 1", sector=sector, camion=camion)
