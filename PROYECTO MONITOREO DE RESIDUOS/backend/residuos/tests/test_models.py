from datetime import date, time

import pytest
from django.core.exceptions import ValidationError

from residuos.models import Horario, Incidencia, PosicionGPS, RecorridoRealizado, Usuario


def test_horario_invalido_lanza_error(ruta):
    h = Horario(ruta=ruta, dia_semana=0, hora_inicio=time(9), hora_fin=time(7))
    with pytest.raises(ValidationError):
        h.clean()


def test_horario_duracion_y_vigencia(ruta):
    h = Horario.objects.create(ruta=ruta, dia_semana=0, hora_inicio=time(7), hora_fin=time(9))
    assert h.duracion_minutos() == 120
    assert h.esta_vigente(time(8, 0))
    assert not h.esta_vigente(time(10, 0))


def test_incidencia_flujo_de_estados(sector):
    inc = Incidencia.objects.create(sector=sector, tipo="Otros")
    assert inc.esta_pendiente()
    inc.cambiar_estado(Incidencia.Estado.EN_PROCESO)
    inc.resolver()
    assert inc.estado == Incidencia.Estado.RESUELTA and inc.fecha_resolucion
    with pytest.raises(ValueError):
        inc.cambiar_estado(Incidencia.Estado.PENDIENTE)


def test_asignar_operador_exige_rol(camion, db):
    ciudadano = Usuario.objects.create_user("vecino", password="x")
    with pytest.raises(ValueError):
        camion.asignar_operador(ciudadano)


def test_ultima_posicion(camion):
    PosicionGPS.objects.create(camion=camion, latitud="-9.93", longitud="-76.24")
    ultima = PosicionGPS.objects.create(camion=camion, latitud="-9.94", longitud="-76.25")
    assert camion.ultima_posicion() == ultima
    assert ultima.dentro_de_zona()


def test_recorrido_cumplido_y_con_retraso(ruta):
    lunes = date(2026, 10, 19)  # es lunes
    Horario.objects.create(ruta=ruta, dia_semana=0, hora_inicio=time(7), hora_fin=time(9))
    a = RecorridoRealizado.objects.create(ruta=ruta, fecha=lunes, hora_inicio_real=time(7, 10),
                                          hora_fin_real=time(9))
    assert a.calcular_cumplimiento() is True
    b = RecorridoRealizado(ruta=ruta, fecha=date(2026, 10, 26), hora_inicio_real=time(8, 45),
                           hora_fin_real=time(9))
    assert b.calcular_cumplimiento() is False
