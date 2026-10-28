"""CP-01 a CP-07 de la Parte 4 (reglas de negocio puras)."""
from datetime import time

import pytest

from residuos.servicios import ValidadorRuta, validar_incidencia


@pytest.fixture
def v():
    return ValidadorRuta()


def test_cp01_horario_correcto(v):
    assert v.horario_valido(time(7, 0), time(9, 0))


def test_cp02_horario_invertido(v):
    assert not v.horario_valido(time(9, 0), time(7, 0))


def test_horario_nulo(v):
    assert not v.horario_valido(None, time(9, 0))


@pytest.mark.parametrize("lat, lon, esperado", [
    (-9.93, -76.24, True),    # CP-03 dentro de zona
    (0.0, 0.0, False),        # CP-04 fuera de zona
])
def test_cp03_cp04_ruta_en_zona(v, lat, lon, esperado):
    assert v.dentro_de_zona(lat, lon) is esperado


@pytest.fixture
def incidencia():
    return {"tipo": "Quema de basura", "sector": "La Esperanza"}


def test_cp05_incidencia_valida(incidencia):
    assert validar_incidencia(incidencia)


@pytest.mark.parametrize("sector", ["La Esperanza", "San Andrés"])
def test_cp06_sectores(incidencia, sector):
    incidencia["sector"] = sector
    assert validar_incidencia(incidencia)


def test_cp07_tipo_invalido(incidencia):
    incidencia["tipo"] = "Spam"
    with pytest.raises(ValueError):
        validar_incidencia(incidencia)


def test_sector_fuera_de_zona(incidencia):
    incidencia["sector"] = "Lima"
    with pytest.raises(ValueError):
        validar_incidencia(incidencia)
