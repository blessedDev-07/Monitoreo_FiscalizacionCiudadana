"""Reglas de negocio puras (sin base de datos).

Son las mismas reglas que se validan en la Parte 4 del trabajo
(JUnit/pytest): horarios, rutas dentro de zona e incidencias válidas.
"""
from datetime import time

# Rectángulo aproximado que cubre La Esperanza y San Andrés (Amarilis).
ZONA = {"lat_min": -10.00, "lat_max": -9.88, "lon_min": -76.30, "lon_max": -76.17}

TIPOS_INCIDENCIA = (
    "No pasó el camión",
    "Conducta inadecuada",
    "Quema de basura",
    "Otros",
)
SECTORES_VALIDOS = ("La Esperanza", "San Andrés")


class ValidadorRuta:
    """Valida horarios y coordenadas GPS de las rutas del camión."""

    def horario_valido(self, inicio: time | None, fin: time | None) -> bool:
        """El inicio debe ser anterior al fin del recorrido."""
        return inicio is not None and fin is not None and inicio < fin

    def dentro_de_zona(self, lat: float, lon: float) -> bool:
        """La coordenada debe caer dentro de La Esperanza o San Andrés."""
        return (
            ZONA["lat_min"] <= float(lat) <= ZONA["lat_max"]
            and ZONA["lon_min"] <= float(lon) <= ZONA["lon_max"]
        )


def validar_incidencia(datos: dict) -> bool:
    """Valida el tipo y el sector de un reporte ciudadano antes de guardarlo."""
    if datos.get("tipo") not in TIPOS_INCIDENCIA:
        raise ValueError("Tipo no válido")
    if datos.get("sector") not in SECTORES_VALIDOS:
        raise ValueError("Sector fuera de zona")
    return True


class EstadisticasService:
    """Genera los indicadores del panel web (dashboard)."""

    @staticmethod
    def resumen_por_sector() -> list[dict]:
        from .models import Camion, Incidencia, RecorridoRealizado, Sector  # evita import circular

        resultado = []
        for sector in Sector.objects.all():
            recorridos = RecorridoRealizado.objects.filter(ruta__sector=sector)
            total_rec = recorridos.count()
            cumplidos = recorridos.filter(cumplido=True).count()
            incidencias = Incidencia.objects.filter(sector=sector)
            resultado.append({
                "sector": sector.nombre,
                "incidencias_total": incidencias.count(),
                "incidencias_pendientes": incidencias.filter(estado=Incidencia.Estado.PENDIENTE).count(),
                "incidencias_resueltas": incidencias.filter(estado=Incidencia.Estado.RESUELTA).count(),
                "recorridos_total": total_rec,
                "recorridos_cumplidos": cumplidos,
                "porcentaje_cumplimiento": round(100 * cumplidos / total_rec, 1) if total_rec else 0.0,
            })
        return resultado

    @staticmethod
    def resumen_general() -> dict:
        from .models import Camion, Incidencia

        return {
            "camiones_total": Camion.objects.count(),
            "camiones_activos": Camion.objects.filter(estado=Camion.Estado.ACTIVO).count(),
            "incidencias_pendientes": Incidencia.objects.filter(estado=Incidencia.Estado.PENDIENTE).count(),
            "sectores": EstadisticasService.resumen_por_sector(),
        }
