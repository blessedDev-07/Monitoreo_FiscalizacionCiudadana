import pytest

from residuos.models import Incidencia


def test_crear_incidencia_valida(cliente, sector):
    r = cliente.post("/api/incidencias/", {"sector": sector.id, "tipo": "Quema de basura",
                                           "descripcion": "Humo"}, format="json")
    assert r.status_code == 201
    assert r.json()["estado"] == "PENDIENTE"


def test_incidencia_tipo_invalido_devuelve_400(cliente, sector):
    r = cliente.post("/api/incidencias/", {"sector": sector.id, "tipo": "Spam"}, format="json")
    assert r.status_code == 400


def test_cambiar_estado_incidencia(cliente, sector):
    inc = Incidencia.objects.create(sector=sector, tipo="Otros")
    ok = cliente.post(f"/api/incidencias/{inc.id}/cambiar-estado/", {"estado": "EN_PROCESO"}, format="json")
    assert ok.status_code == 200
    mal = cliente.post(f"/api/incidencias/{inc.id}/cambiar-estado/", {"estado": "PENDIENTE"}, format="json")
    assert mal.status_code == 400


def test_registrar_gps_y_consultar_posiciones_actuales(cliente, camion):
    cliente.post("/api/posiciones/", {"camion": camion.id, "latitud": "-9.930000", "longitud": "-76.240000"},
                 format="json")
    r = cliente.post("/api/posiciones/", {"camion": camion.id, "latitud": "-9.931000", "longitud": "-76.241000"},
                     format="json")
    assert r.status_code == 201
    actuales = cliente.get("/api/camiones/posiciones-actuales/").json()
    assert len(actuales) == 1 and actuales[0]["latitud"] == "-9.931000"


def test_gps_fuera_de_zona_rechazado(cliente, camion):
    r = cliente.post("/api/posiciones/", {"camion": camion.id, "latitud": "0", "longitud": "0"}, format="json")
    assert r.status_code == 400


def test_horario_invertido_rechazado(cliente, ruta):
    r = cliente.post("/api/horarios/", {"ruta": ruta.id, "dia_semana": 0, "hora_inicio": "09:00",
                                        "hora_fin": "07:00"}, format="json")
    assert r.status_code == 400


def test_estadisticas(cliente, sector, camion):
    Incidencia.objects.create(sector=sector, tipo="Otros")
    datos = cliente.get("/api/estadisticas/resumen/").json()
    assert datos["camiones_activos"] == 1
    assert datos["sectores"][0]["incidencias_pendientes"] == 1
