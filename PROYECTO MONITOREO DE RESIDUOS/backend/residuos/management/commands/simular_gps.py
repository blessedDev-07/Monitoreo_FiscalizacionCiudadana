"""Simula el GPS de los camiones recorriendo sus rutas (demo en tiempo real)."""
import random
import time as reloj
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from residuos.models import Camion, PosicionGPS


class Command(BaseCommand):
    help = "Envía posiciones GPS simuladas de cada camión cada N segundos (Ctrl+C para detener)"

    def add_arguments(self, parser):
        parser.add_argument("--intervalo", type=float, default=3.0, help="segundos entre posiciones")
        parser.add_argument("--pasos", type=int, default=0, help="0 = infinito")

    def handle(self, *args, **opciones):
        trazas = {}
        for camion in Camion.objects.filter(estado=Camion.Estado.ACTIVO):
            ruta = camion.rutas.first()
            puntos = list(ruta.puntos.all()) if ruta else []
            if len(puntos) >= 2:
                trazas[camion] = [(float(p.latitud), float(p.longitud)) for p in puntos]
        if not trazas:
            self.stdout.write(self.style.WARNING("No hay camiones con ruta. Ejecuta: python manage.py cargar_datos"))
            return

        self.stdout.write(self.style.SUCCESS(f"Simulando {len(trazas)} camiones. Ctrl+C para detener."))
        paso, subpasos = 0, 10
        try:
            while True:
                for camion, traza in trazas.items():
                    # Ida y vuelta sobre los puntos de la ruta, interpolando entre ellos.
                    tramos = len(traza) - 1
                    recorrido = (paso // subpasos) % (tramos * 2)
                    ida = recorrido < tramos
                    i = recorrido if ida else (tramos * 2 - 1 - recorrido)
                    a, b = (traza[i], traza[i + 1]) if ida else (traza[i + 1], traza[i])
                    f = (paso % subpasos) / subpasos
                    lat = a[0] + (b[0] - a[0]) * f + random.uniform(-0.00003, 0.00003)
                    lon = a[1] + (b[1] - a[1]) * f + random.uniform(-0.00003, 0.00003)
                    PosicionGPS.objects.create(camion=camion, latitud=Decimal(f"{lat:.6f}"),
                                               longitud=Decimal(f"{lon:.6f}"),
                                               velocidad_kmh=round(random.uniform(10, 25), 1),
                                               fecha_hora=timezone.now())
                paso += 1
                if opciones["pasos"] and paso >= opciones["pasos"]:
                    break
                reloj.sleep(opciones["intervalo"])
        except KeyboardInterrupt:
            self.stdout.write("\nSimulación detenida.")
