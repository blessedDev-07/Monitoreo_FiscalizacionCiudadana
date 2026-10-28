"""Carga datos de ejemplo: sectores, usuarios, camiones, rutas, horarios e incidencias."""
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from residuos.models import (Camion, Horario, Incidencia, PuntoRuta,
                             RecorridoRealizado, Ruta, Sector, Usuario)

# Coordenadas aproximadas de ejemplo dentro de la zona piloto (Amarilis, Huánuco).
RUTAS = [
    {
        "nombre": "Ruta La Esperanza – Mañana", "sector": "La Esperanza", "camion": "AM-01",
        "inicio": time(7, 0), "fin": time(9, 0),
        "puntos": [(-9.9300, -76.2450, "Jr. Los Pinos"), (-9.9320, -76.2420, "Jr. Las Flores"),
                   (-9.9345, -76.2390, "Pasaje Los Olivos"), (-9.9370, -76.2360, "Jr. Progreso"),
                   (-9.9390, -76.2330, "Jr. Esperanza")],
    },
    {
        "nombre": "Ruta San Andrés – Mañana", "sector": "San Andrés", "camion": "AM-02",
        "inicio": time(8, 0), "fin": time(10, 0),
        "puntos": [(-9.9150, -76.2520, "Jr. San Andrés"), (-9.9170, -76.2490, "Jr. Los Laureles"),
                   (-9.9195, -76.2460, "Pasaje Las Palmas"), (-9.9220, -76.2430, "Jr. Libertad"),
                   (-9.9245, -76.2400, "Av. Universitaria")],
    },
    {
        "nombre": "Ruta La Esperanza – Tarde", "sector": "La Esperanza", "camion": "AM-03",
        "inicio": time(15, 0), "fin": time(17, 0),
        "puntos": [(-9.9280, -76.2300, "Jr. Arequipa"), (-9.9300, -76.2330, "Jr. Cusco"),
                   (-9.9325, -76.2360, "Jr. Tacna"), (-9.9350, -76.2390, "Jr. Lima")],
    },
]


class Command(BaseCommand):
    help = "Carga datos de ejemplo para el Sistema de Monitoreo de Residuos Sólidos – Amarilis"

    def handle(self, *args, **opciones):
        esperanza, _ = Sector.objects.get_or_create(nombre="La Esperanza", defaults={"descripcion": "Sector piloto"})
        andres, _ = Sector.objects.get_or_create(nombre="San Andrés", defaults={"descripcion": "Sector piloto"})
        sectores = {"La Esperanza": esperanza, "San Andrés": andres}

        if not Usuario.objects.filter(username="admin").exists():
            Usuario.objects.create_superuser("admin", "admin@amarilis.pe", "admin123",
                                             rol=Usuario.Rol.ADMINISTRADOR)

        operadores = []
        for i, nombre in enumerate(["Carlos", "Luis", "Pedro"], start=1):
            op, creado = Usuario.objects.get_or_create(
                username=f"operador{i}",
                defaults={"first_name": nombre, "last_name": "Operador", "rol": Usuario.Rol.OPERADOR})
            if creado:
                op.set_password("operador123")
                op.save()
            operadores.append(op)

        camiones = {}
        for i, op in enumerate(operadores, start=1):
            camiones[f"AM-0{i}"], _ = Camion.objects.get_or_create(
                codigo=f"AM-0{i}", defaults={"placa": f"XYZ-10{i}", "operador": op})

        for datos in RUTAS:
            ruta, creada = Ruta.objects.get_or_create(
                nombre=datos["nombre"],
                defaults={"sector": sectores[datos["sector"]], "camion": camiones[datos["camion"]]})
            if not creada:
                continue
            for dia in range(0, 6):  # lunes a sábado
                Horario.objects.create(ruta=ruta, dia_semana=dia,
                                       hora_inicio=datos["inicio"], hora_fin=datos["fin"])
            for orden, (lat, lon, ref) in enumerate(datos["puntos"], start=1):
                PuntoRuta.objects.create(ruta=ruta, orden=orden, latitud=Decimal(str(lat)),
                                         longitud=Decimal(str(lon)), referencia=ref)
            # Historial de recorridos de los últimos 5 días (uno tarde, para mostrar % de cumplimiento).
            for atras in range(1, 6):
                dia = date.today() - timedelta(days=atras)
                if dia.weekday() == 6:
                    continue
                retraso = 90 if atras == 3 else 5
                inicio = (time(datos["inicio"].hour, datos["inicio"].minute))
                real = time(inicio.hour + retraso // 60, (inicio.minute + retraso) % 60)
                rec = RecorridoRealizado(ruta=ruta, fecha=dia, hora_inicio_real=real,
                                         hora_fin_real=datos["fin"])
                rec.calcular_cumplimiento()
                rec.save()

        if not Incidencia.objects.exists():
            Incidencia.objects.create(sector=esperanza, tipo="Quema de basura",
                                      descripcion="Queman residuos en el terreno baldío.")
            Incidencia.objects.create(sector=andres, tipo="No pasó el camión",
                                      descripcion="No pasó el camión el día de hoy.")
            Incidencia.objects.create(sector=esperanza, tipo="Conducta inadecuada",
                                      descripcion="Personal arrojó residuos en la vía.")

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados. Admin: admin / admin123"))
