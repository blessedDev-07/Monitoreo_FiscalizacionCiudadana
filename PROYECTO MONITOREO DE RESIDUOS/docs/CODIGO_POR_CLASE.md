# Código de cada clase

## Modelos (una clase = una clase del UML)
`backend/residuos/models.py`

```python
"""Modelo de dominio: una clase del diagrama UML = un modelo de Django."""
from datetime import datetime, timedelta

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .servicios import TIPOS_INCIDENCIA, ValidadorRuta

validador = ValidadorRuta()


# ---------------------------------------------------------------- Sector
class Sector(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def total_incidencias(self) -> int:
        return self.incidencias.count()

    def incidencias_pendientes(self) -> int:
        return self.incidencias.filter(estado=Incidencia.Estado.PENDIENTE).count()


# --------------------------------------------------------------- Usuario
class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        CIUDADANO = "CIUDADANO", "Ciudadano"
        OPERADOR = "OPERADOR", "Operador"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"

    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.CIUDADANO)
    telefono = models.CharField(max_length=15, blank=True)
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="residentes")

    def es_operador(self) -> bool:
        return self.rol == self.Rol.OPERADOR

    def es_administrador(self) -> bool:
        return self.rol == self.Rol.ADMINISTRADOR

    def nombre_completo(self) -> str:
        return self.get_full_name() or self.username


# ---------------------------------------------------------------- Camion
class Camion(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        MANTENIMIENTO = "MANTENIMIENTO", "En mantenimiento"
        INACTIVO = "INACTIVO", "Inactivo"

    codigo = models.CharField(max_length=10, unique=True)  # p. ej. AM-01
    placa = models.CharField(max_length=10, unique=True)
    capacidad_kg = models.PositiveIntegerField(default=5000)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.ACTIVO)
    operador = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="camiones", limit_choices_to={"rol": "OPERADOR"})

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} ({self.placa})"

    def esta_activo(self) -> bool:
        return self.estado == self.Estado.ACTIVO

    def ultima_posicion(self):
        return self.posiciones.first()  # ordering = -fecha_hora

    def asignar_operador(self, usuario: Usuario) -> None:
        if not usuario.es_operador():
            raise ValueError("El usuario no tiene rol de operador")
        self.operador = usuario
        self.save(update_fields=["operador"])

    def cambiar_estado(self, nuevo: str) -> None:
        if nuevo not in self.Estado.values:
            raise ValueError("Estado de camión no válido")
        self.estado = nuevo
        self.save(update_fields=["estado"])


# ------------------------------------------------------------------ Ruta
class Ruta(models.Model):
    nombre = models.CharField(max_length=100)
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="rutas")
    camion = models.ForeignKey(Camion, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="rutas")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def horario_del_dia(self, dia: int | None = None):
        dia = timezone.localtime().weekday() if dia is None else dia
        return self.horarios.filter(dia_semana=dia).first()

    def esta_en_servicio(self, ahora: datetime | None = None) -> bool:
        ahora = timezone.localtime(ahora) if ahora else timezone.localtime()
        horario = self.horario_del_dia(ahora.weekday())
        return bool(self.activa and horario and horario.esta_vigente(ahora.time()))

    def total_puntos(self) -> int:
        return self.puntos.count()


class PuntoRuta(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="puntos")
    orden = models.PositiveIntegerField()
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    referencia = models.CharField(max_length=120, blank=True)  # jirón / pasaje

    class Meta:
        ordering = ["ruta", "orden"]
        constraints = [models.UniqueConstraint(fields=["ruta", "orden"], name="punto_unico_por_orden")]

    def __str__(self):
        return f"{self.ruta} #{self.orden}"

    def dentro_de_zona(self) -> bool:
        return validador.dentro_de_zona(self.latitud, self.longitud)

    def clean(self):
        if not self.dentro_de_zona():
            raise ValidationError("El punto está fuera de La Esperanza / San Andrés")


# --------------------------------------------------------------- Horario
class Horario(models.Model):
    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="horarios")
    dia_semana = models.IntegerField(choices=Dia.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ["ruta", "dia_semana"]
        constraints = [models.UniqueConstraint(fields=["ruta", "dia_semana"], name="horario_unico_por_dia")]

    def __str__(self):
        return f"{self.ruta} · {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"

    def es_valido(self) -> bool:
        return validador.horario_valido(self.hora_inicio, self.hora_fin)

    def esta_vigente(self, hora) -> bool:
        return self.es_valido() and self.hora_inicio <= hora <= self.hora_fin

    def duracion_minutos(self) -> int:
        if not self.es_valido():
            return 0
        hoy = datetime.today().date()
        return int((datetime.combine(hoy, self.hora_fin) - datetime.combine(hoy, self.hora_inicio)).total_seconds() // 60)

    def clean(self):
        if not self.es_valido():
            raise ValidationError("La hora de inicio debe ser anterior a la hora de fin")


# ----------------------------------------------------------- PosicionGPS
class PosicionGPS(models.Model):
    camion = models.ForeignKey(Camion, on_delete=models.CASCADE, related_name="posiciones")
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    velocidad_kmh = models.FloatField(default=0)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha_hora"]
        indexes = [models.Index(fields=["camion", "-fecha_hora"])]
        verbose_name = "posición GPS"
        verbose_name_plural = "posiciones GPS"

    def __str__(self):
        return f"{self.camion.codigo} @ {self.latitud},{self.longitud}"

    def dentro_de_zona(self) -> bool:
        return validador.dentro_de_zona(self.latitud, self.longitud)


# ------------------------------------------------------------ Incidencia
class Incidencia(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        RESUELTA = "RESUELTA", "Resuelta"

    TRANSICIONES = {
        Estado.PENDIENTE: {Estado.EN_PROCESO, Estado.RESUELTA},
        Estado.EN_PROCESO: {Estado.RESUELTA},
        Estado.RESUELTA: set(),
    }

    ciudadano = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="incidencias")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="incidencias")
    tipo = models.CharField(max_length=40, choices=[(t, t) for t in TIPOS_INCIDENCIA])
    descripcion = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.tipo} – {self.sector} ({self.estado})"

    def esta_pendiente(self) -> bool:
        return self.estado == self.Estado.PENDIENTE

    def validar(self) -> bool:
        from .servicios import validar_incidencia
        return validar_incidencia({"tipo": self.tipo, "sector": self.sector.nombre})

    def cambiar_estado(self, nuevo: str) -> None:
        if nuevo not in self.TRANSICIONES.get(self.estado, set()):
            raise ValueError(f"No se puede pasar de {self.estado} a {nuevo}")
        self.estado = nuevo
        if nuevo == self.Estado.RESUELTA:
            self.fecha_resolucion = timezone.now()
        self.save(update_fields=["estado", "fecha_resolucion"])

    def resolver(self) -> None:
        self.cambiar_estado(self.Estado.RESUELTA)


# ------------------------------------------------------ RecorridoRealizado
class RecorridoRealizado(models.Model):
    """Registro diario de fiscalización: ¿el camión cumplió su ruta y horario?"""

    TOLERANCIA_MIN = 30

    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name="recorridos")
    fecha = models.DateField(default=timezone.localdate)
    hora_inicio_real = models.TimeField(null=True, blank=True)
    hora_fin_real = models.TimeField(null=True, blank=True)
    cumplido = models.BooleanField(default=False)
    observaciones = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-fecha"]
        constraints = [models.UniqueConstraint(fields=["ruta", "fecha"], name="un_recorrido_por_dia")]

    def __str__(self):
        return f"{self.ruta} · {self.fecha}"

    def registrar_inicio(self, hora=None) -> None:
        self.hora_inicio_real = hora or timezone.localtime().time().replace(microsecond=0)
        self.save(update_fields=["hora_inicio_real"])

    def registrar_fin(self, hora=None) -> None:
        self.hora_fin_real = hora or timezone.localtime().time().replace(microsecond=0)
        self.calcular_cumplimiento()
        self.save(update_fields=["hora_fin_real", "cumplido"])

    def retraso_minutos(self) -> int | None:
        horario = self.ruta.horario_del_dia(self.fecha.weekday())
        if not (horario and self.hora_inicio_real):
            return None
        base = datetime.combine(self.fecha, horario.hora_inicio)
        real = datetime.combine(self.fecha, self.hora_inicio_real)
        return int((real - base).total_seconds() // 60)

    def calcular_cumplimiento(self) -> bool:
        retraso = self.retraso_minutos()
        self.cumplido = bool(self.hora_fin_real and retraso is not None and retraso <= self.TOLERANCIA_MIN)
        return self.cumplido

```

## Reglas de negocio: ValidadorRuta, validar_incidencia, EstadisticasService
`backend/residuos/servicios.py`

```python
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

```

## Serializers
`backend/residuos/serializers.py`

```python
from rest_framework import serializers

from .models import (Camion, Horario, Incidencia, PosicionGPS, PuntoRuta,
                     RecorridoRealizado, Ruta, Sector, Usuario, validador)
from .servicios import validar_incidencia


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ["id", "nombre", "descripcion"]


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "rol", "telefono", "sector"]


class PosicionGPSSerializer(serializers.ModelSerializer):
    camion_codigo = serializers.CharField(source="camion.codigo", read_only=True)

    class Meta:
        model = PosicionGPS
        fields = ["id", "camion", "camion_codigo", "latitud", "longitud", "velocidad_kmh", "fecha_hora"]

    def validate(self, datos):
        if not validador.dentro_de_zona(datos["latitud"], datos["longitud"]):
            raise serializers.ValidationError("La coordenada está fuera de La Esperanza / San Andrés")
        return datos


class CamionSerializer(serializers.ModelSerializer):
    ultima_posicion = serializers.SerializerMethodField()
    operador_nombre = serializers.CharField(source="operador.nombre_completo", read_only=True, default=None)

    class Meta:
        model = Camion
        fields = ["id", "codigo", "placa", "capacidad_kg", "estado", "operador",
                  "operador_nombre", "ultima_posicion"]

    def get_ultima_posicion(self, camion):
        pos = camion.ultima_posicion()
        return PosicionGPSSerializer(pos).data if pos else None


class PuntoRutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoRuta
        fields = ["id", "ruta", "orden", "latitud", "longitud", "referencia"]

    def validate(self, datos):
        if not validador.dentro_de_zona(datos["latitud"], datos["longitud"]):
            raise serializers.ValidationError("El punto está fuera de La Esperanza / San Andrés")
        return datos


class HorarioSerializer(serializers.ModelSerializer):
    dia_nombre = serializers.CharField(source="get_dia_semana_display", read_only=True)

    class Meta:
        model = Horario
        fields = ["id", "ruta", "dia_semana", "dia_nombre", "hora_inicio", "hora_fin"]

    def validate(self, datos):
        if not validador.horario_valido(datos["hora_inicio"], datos["hora_fin"]):
            raise serializers.ValidationError("La hora de inicio debe ser anterior a la hora de fin")
        return datos


class RutaSerializer(serializers.ModelSerializer):
    sector_nombre = serializers.CharField(source="sector.nombre", read_only=True)
    camion_codigo = serializers.CharField(source="camion.codigo", read_only=True, default=None)
    horarios = HorarioSerializer(many=True, read_only=True)
    puntos = PuntoRutaSerializer(many=True, read_only=True)
    en_servicio = serializers.SerializerMethodField()

    class Meta:
        model = Ruta
        fields = ["id", "nombre", "sector", "sector_nombre", "camion", "camion_codigo",
                  "activa", "en_servicio", "horarios", "puntos"]

    def get_en_servicio(self, ruta):
        return ruta.esta_en_servicio()


class IncidenciaSerializer(serializers.ModelSerializer):
    sector_nombre = serializers.CharField(source="sector.nombre", read_only=True)

    class Meta:
        model = Incidencia
        fields = ["id", "ciudadano", "sector", "sector_nombre", "tipo", "descripcion",
                  "latitud", "longitud", "estado", "fecha_creacion", "fecha_resolucion"]
        read_only_fields = ["estado", "fecha_creacion", "fecha_resolucion"]

    def validate(self, datos):
        try:
            validar_incidencia({"tipo": datos.get("tipo"), "sector": datos["sector"].nombre})
        except ValueError as error:
            raise serializers.ValidationError(str(error))
        return datos


class RecorridoSerializer(serializers.ModelSerializer):
    ruta_nombre = serializers.CharField(source="ruta.nombre", read_only=True)
    retraso_minutos = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecorridoRealizado
        fields = ["id", "ruta", "ruta_nombre", "fecha", "hora_inicio_real", "hora_fin_real",
                  "cumplido", "retraso_minutos", "observaciones"]
        read_only_fields = ["cumplido"]

```

## Vistas / ViewSets
`backend/residuos/views.py`

```python
from django.db.models import OuterRef, Subquery
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (Camion, Horario, Incidencia, PosicionGPS, PuntoRuta,
                     RecorridoRealizado, Ruta, Sector)
from .serializers import (CamionSerializer, HorarioSerializer, IncidenciaSerializer,
                          PosicionGPSSerializer, PuntoRutaSerializer, RecorridoSerializer,
                          RutaSerializer, SectorSerializer)
from .servicios import EstadisticasService


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


class CamionViewSet(viewsets.ModelViewSet):
    queryset = Camion.objects.select_related("operador").all()
    serializer_class = CamionSerializer

    @action(detail=False, methods=["get"], url_path="posiciones-actuales")
    def posiciones_actuales(self, request):
        """Última posición GPS de cada camión (para el mapa en tiempo real)."""
        ultima = PosicionGPS.objects.filter(camion=OuterRef("pk")).order_by("-fecha_hora")
        ids = Camion.objects.annotate(pos=Subquery(ultima.values("pk")[:1])).values_list("pos", flat=True)
        posiciones = PosicionGPS.objects.filter(pk__in=[i for i in ids if i]).select_related("camion")
        return Response(PosicionGPSSerializer(posiciones, many=True).data)

    @action(detail=True, methods=["get"])
    def recorrido(self, request, pk=None):
        """Últimas 100 posiciones del camión (traza del recorrido)."""
        posiciones = self.get_object().posiciones.all()[:100]
        return Response(PosicionGPSSerializer(posiciones, many=True).data)


class PosicionGPSViewSet(viewsets.ModelViewSet):
    """La app del operador envía aquí las coordenadas GPS."""
    queryset = PosicionGPS.objects.select_related("camion").all()
    serializer_class = PosicionGPSSerializer
    http_method_names = ["get", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        posiciones = self.get_queryset()
        camion = request.query_params.get("camion")
        if camion:
            posiciones = posiciones.filter(camion_id=camion)
        return Response(self.get_serializer(posiciones[:200], many=True).data)


class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.select_related("sector", "camion").prefetch_related("horarios", "puntos")
    serializer_class = RutaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        sector = self.request.query_params.get("sector")
        return qs.filter(sector_id=sector) if sector else qs


class PuntoRutaViewSet(viewsets.ModelViewSet):
    queryset = PuntoRuta.objects.all()
    serializer_class = PuntoRutaSerializer


class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer


class IncidenciaViewSet(viewsets.ModelViewSet):
    queryset = Incidencia.objects.select_related("sector").all()
    serializer_class = IncidenciaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("sector"):
            qs = qs.filter(sector_id=p["sector"])
        if p.get("estado"):
            qs = qs.filter(estado=p["estado"])
        return qs

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        incidencia = self.get_object()
        try:
            incidencia.cambiar_estado(request.data.get("estado"))
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(incidencia).data)


class RecorridoViewSet(viewsets.ModelViewSet):
    queryset = RecorridoRealizado.objects.select_related("ruta").all()
    serializer_class = RecorridoSerializer

    @action(detail=False, methods=["post"])
    def iniciar(self, request):
        ruta = Ruta.objects.filter(pk=request.data.get("ruta")).first()
        if not ruta:
            return Response({"detail": "Ruta no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        recorrido, _ = RecorridoRealizado.objects.get_or_create(ruta=ruta)
        recorrido.registrar_inicio()
        return Response(self.get_serializer(recorrido).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        recorrido = self.get_object()
        recorrido.registrar_fin()
        return Response(self.get_serializer(recorrido).data)


class EstadisticasView(APIView):
    """Datos del panel web: cumplimiento de rutas e incidencias por sector."""

    def get(self, request):
        return Response(EstadisticasService.resumen_general())

```

## URLs de la API
`backend/residuos/urls.py`

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sectores", views.SectorViewSet)
router.register("camiones", views.CamionViewSet)
router.register("posiciones", views.PosicionGPSViewSet)
router.register("rutas", views.RutaViewSet)
router.register("puntos-ruta", views.PuntoRutaViewSet)
router.register("horarios", views.HorarioViewSet)
router.register("incidencias", views.IncidenciaViewSet)
router.register("recorridos", views.RecorridoViewSet)

urlpatterns = [
    path("estadisticas/resumen/", views.EstadisticasView.as_view()),
    path("", include(router.urls)),
]

```

## Admin
`backend/residuos/admin.py`

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (Camion, Horario, Incidencia, PosicionGPS, PuntoRuta,
                     RecorridoRealizado, Ruta, Sector, Usuario)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Datos del sistema", {"fields": ("rol", "telefono", "sector")}),)
    list_display = ("username", "first_name", "last_name", "rol", "sector")


for modelo in (Sector, Camion, Ruta, PuntoRuta, Horario, PosicionGPS, Incidencia, RecorridoRealizado):
    admin.site.register(modelo)

```

## Configuración
`backend/config/settings.py`

```python
"""Configuración del Sistema de Monitoreo de Residuos Sólidos – Amarilis."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-cambiar-en-produccion"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "residuos",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "residuos.Usuario"

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer",
                                 "rest_framework.renderers.BrowsableAPIRenderer"],
}

# --- CORS: permite que Angular (puerto 4200) consuma la API ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

```

## Comando: cargar_datos
`backend/residuos/management/commands/cargar_datos.py`

```python
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

```

## Comando: simular_gps
`backend/residuos/management/commands/simular_gps.py`

```python
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

```

## Pruebas: test_servicios.py
`backend/residuos/tests/test_servicios.py`

```python
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

```

## Pruebas: test_models.py
`backend/residuos/tests/test_models.py`

```python
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

```

## Pruebas: test_api.py
`backend/residuos/tests/test_api.py`

```python
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

```

## Angular: interfaces
`frontend/src/app/models/models.ts`

```typescript
// Interfaces TypeScript: reflejan las clases del diagrama UML / la API de Django.

export type Rol = 'CIUDADANO' | 'OPERADOR' | 'ADMINISTRADOR';
export type EstadoCamion = 'ACTIVO' | 'MANTENIMIENTO' | 'INACTIVO';
export type EstadoIncidencia = 'PENDIENTE' | 'EN_PROCESO' | 'RESUELTA';

export const TIPOS_INCIDENCIA = [
  'No pasó el camión',
  'Conducta inadecuada',
  'Quema de basura',
  'Otros',
] as const;

export interface Sector {
  id: number;
  nombre: string;
  descripcion: string;
}

export interface PosicionGPS {
  id: number;
  camion: number;
  camion_codigo: string;
  latitud: string;
  longitud: string;
  velocidad_kmh: number;
  fecha_hora: string;
}

export interface Camion {
  id: number;
  codigo: string;
  placa: string;
  capacidad_kg: number;
  estado: EstadoCamion;
  operador: number | null;
  operador_nombre: string | null;
  ultima_posicion: PosicionGPS | null;
}

export interface PuntoRuta {
  id: number;
  ruta: number;
  orden: number;
  latitud: string;
  longitud: string;
  referencia: string;
}

export interface Horario {
  id: number;
  ruta: number;
  dia_semana: number;
  dia_nombre: string;
  hora_inicio: string;
  hora_fin: string;
}

export interface Ruta {
  id: number;
  nombre: string;
  sector: number;
  sector_nombre: string;
  camion: number | null;
  camion_codigo: string | null;
  activa: boolean;
  en_servicio: boolean;
  horarios: Horario[];
  puntos: PuntoRuta[];
}

export interface Incidencia {
  id: number;
  sector: number;
  sector_nombre: string;
  tipo: string;
  descripcion: string;
  latitud: string | null;
  longitud: string | null;
  estado: EstadoIncidencia;
  fecha_creacion: string;
  fecha_resolucion: string | null;
}

export interface ResumenSector {
  sector: string;
  incidencias_total: number;
  incidencias_pendientes: number;
  incidencias_resueltas: number;
  recorridos_total: number;
  recorridos_cumplidos: number;
  porcentaje_cumplimiento: number;
}

export interface ResumenGeneral {
  camiones_total: number;
  camiones_activos: number;
  incidencias_pendientes: number;
  sectores: ResumenSector[];
}

```

## Angular: servicio API
`frontend/src/app/services/api.service.ts`

```typescript
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Camion, EstadoIncidencia, Incidencia, PosicionGPS, ResumenGeneral, Ruta, Sector,
} from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  sectores(): Observable<Sector[]> {
    return this.http.get<Sector[]>(`${this.base}/sectores/`);
  }
  camiones(): Observable<Camion[]> {
    return this.http.get<Camion[]>(`${this.base}/camiones/`);
  }
  posicionesActuales(): Observable<PosicionGPS[]> {
    return this.http.get<PosicionGPS[]>(`${this.base}/camiones/posiciones-actuales/`);
  }
  rutas(): Observable<Ruta[]> {
    return this.http.get<Ruta[]>(`${this.base}/rutas/`);
  }
  incidencias(estado?: string): Observable<Incidencia[]> {
    const q = estado ? `?estado=${estado}` : '';
    return this.http.get<Incidencia[]>(`${this.base}/incidencias/${q}`);
  }
  crearIncidencia(datos: { sector: number; tipo: string; descripcion: string }): Observable<Incidencia> {
    return this.http.post<Incidencia>(`${this.base}/incidencias/`, datos);
  }
  cambiarEstado(id: number, estado: EstadoIncidencia): Observable<Incidencia> {
    return this.http.post<Incidencia>(`${this.base}/incidencias/${id}/cambiar-estado/`, { estado });
  }
  resumen(): Observable<ResumenGeneral> {
    return this.http.get<ResumenGeneral>(`${this.base}/estadisticas/resumen/`);
  }
}

```

## Angular: panel / mapa
`frontend/src/app/pages/dashboard.component.ts`

```typescript
import { AfterViewInit, Component, OnDestroy, OnInit, inject } from '@angular/core';
import * as L from 'leaflet';
import { interval, startWith, Subscription, switchMap } from 'rxjs';
import { PosicionGPS, ResumenGeneral } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  template: `
    <div class="rejilla">
      <div class="tarjeta"><div>Camiones activos</div>
        <div class="num">{{ resumen?.camiones_activos ?? '–' }} / {{ resumen?.camiones_total ?? '–' }}</div></div>
      <div class="tarjeta"><div>Incidencias pendientes</div>
        <div class="num">{{ resumen?.incidencias_pendientes ?? '–' }}</div></div>
    </div>

    <div class="tarjeta">
      <h2>Camiones en tiempo real</h2>
      <div id="mapa"></div>
      <small>Se actualiza cada 4 segundos. Si no ves camiones ejecuta: <code>python manage.py simular_gps</code></small>
    </div>

    <div class="tarjeta">
      <h2>Cumplimiento e incidencias por sector</h2>
      <table>
        <thead><tr><th>Sector</th><th>Recorridos</th><th>Cumplimiento</th><th>Incidencias</th><th>Pendientes</th></tr></thead>
        <tbody>
          @for (s of resumen?.sectores; track s.sector) {
            <tr>
              <td>{{ s.sector }}</td>
              <td>{{ s.recorridos_cumplidos }} / {{ s.recorridos_total }}</td>
              <td>{{ s.porcentaje_cumplimiento }} %</td>
              <td>{{ s.incidencias_total }}</td>
              <td>{{ s.incidencias_pendientes }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: [`#mapa { height: 420px; border-radius: 10px; margin-bottom: .5rem; }`],
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  private api = inject(ApiService);
  resumen: ResumenGeneral | null = null;
  private mapa?: L.Map;
  private marcadores = new Map<number, L.Marker>();
  private suscripcion = new Subscription();

  ngOnInit(): void {
    this.api.resumen().subscribe(r => (this.resumen = r));
  }

  ngAfterViewInit(): void {
    this.mapa = L.map('mapa').setView([-9.93, -76.24], 14);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.mapa);

    this.suscripcion.add(
      interval(4000)
        .pipe(startWith(0), switchMap(() => this.api.posicionesActuales()))
        .subscribe(posiciones => this.dibujar(posiciones)),
    );
  }

  private dibujar(posiciones: PosicionGPS[]): void {
    for (const p of posiciones) {
      const punto: L.LatLngExpression = [Number(p.latitud), Number(p.longitud)];
      const existente = this.marcadores.get(p.camion);
      if (existente) {
        existente.setLatLng(punto);
      } else {
        const icono = L.divIcon({ html: '🚛', className: 'icono-camion', iconSize: [28, 28] });
        const m = L.marker(punto, { icon: icono })
          .addTo(this.mapa!)
          .bindTooltip(p.camion_codigo, { permanent: true, direction: 'top' });
        this.marcadores.set(p.camion, m);
      }
    }
  }

  ngOnDestroy(): void {
    this.suscripcion.unsubscribe();
    this.mapa?.remove();
  }
}

```

## Angular: incidencias
`frontend/src/app/pages/incidencias.component.ts`

```typescript
import { DatePipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { EstadoIncidencia, Incidencia, Sector, TIPOS_INCIDENCIA } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-incidencias',
  standalone: true,
  imports: [ReactiveFormsModule, DatePipe],
  template: `
    <div class="tarjeta">
      <h2>Reportar incidencia</h2>
      <form [formGroup]="form" (ngSubmit)="enviar()">
        <label>Tipo de reporte</label>
        <select formControlName="tipo">
          @for (t of tipos; track t) { <option [value]="t">{{ t }}</option> }
        </select>
        <label>Sector</label>
        <select formControlName="sector">
          @for (s of sectores; track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }
        </select>
        <label>Descripción</label>
        <textarea rows="3" formControlName="descripcion"></textarea>
        <p><button type="submit" [disabled]="form.invalid">Enviar reporte</button></p>
        @if (mensaje) { <p class="ok">{{ mensaje }}</p> }
        @if (error) { <p class="error">{{ error }}</p> }
      </form>
    </div>

    <div class="tarjeta">
      <h2>Incidencias reportadas</h2>
      <table>
        <thead><tr><th>Fecha</th><th>Tipo</th><th>Sector</th><th>Estado</th><th>Acción</th></tr></thead>
        <tbody>
          @for (i of incidencias; track i.id) {
            <tr>
              <td>{{ i.fecha_creacion | date: 'dd/MM/yyyy HH:mm' }}</td>
              <td>{{ i.tipo }}<br><small>{{ i.descripcion }}</small></td>
              <td>{{ i.sector_nombre }}</td>
              <td><span [class]="'etiqueta ' + i.estado">{{ i.estado }}</span></td>
              <td>
                @if (i.estado === 'PENDIENTE') { <button (click)="cambiar(i, 'EN_PROCESO')">Atender</button> }
                @if (i.estado === 'EN_PROCESO') { <button (click)="cambiar(i, 'RESUELTA')">Resolver</button> }
              </td>
            </tr>
          } @empty { <tr><td colspan="5">Aún no hay reportes.</td></tr> }
        </tbody>
      </table>
    </div>
  `,
})
export class IncidenciasComponent implements OnInit {
  private api = inject(ApiService);
  private fb = inject(FormBuilder);

  tipos = TIPOS_INCIDENCIA;
  sectores: Sector[] = [];
  incidencias: Incidencia[] = [];
  mensaje = '';
  error = '';

  form = this.fb.nonNullable.group({
    tipo: [TIPOS_INCIDENCIA[0] as string, Validators.required],
    sector: [0, [Validators.required, Validators.min(1)]],
    descripcion: [''],
  });

  ngOnInit(): void {
    this.api.sectores().subscribe(s => {
      this.sectores = s;
      if (s.length) this.form.patchValue({ sector: s[0].id });
    });
    this.cargar();
  }

  cargar(): void {
    this.api.incidencias().subscribe(i => (this.incidencias = i));
  }

  enviar(): void {
    this.mensaje = this.error = '';
    this.api.crearIncidencia(this.form.getRawValue()).subscribe({
      next: () => {
        this.mensaje = 'Reporte enviado correctamente.';
        this.form.patchValue({ descripcion: '' });
        this.cargar();
      },
      error: e => (this.error = JSON.stringify(e.error)),
    });
  }

  cambiar(i: Incidencia, estado: EstadoIncidencia): void {
    this.api.cambiarEstado(i.id, estado).subscribe(() => this.cargar());
  }
}

```

## Angular: rutas
`frontend/src/app/pages/rutas.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { Ruta } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-rutas',
  standalone: true,
  template: `
    @for (r of rutas; track r.id) {
      <div class="tarjeta">
        <h2>{{ r.nombre }}
          @if (r.en_servicio) { <span class="etiqueta ACTIVO">En servicio ahora</span> }
        </h2>
        <p>Sector: <b>{{ r.sector_nombre }}</b> · Camión: <b>{{ r.camion_codigo ?? 'sin asignar' }}</b></p>
        <table>
          <thead><tr><th>Día</th><th>Inicio</th><th>Fin</th></tr></thead>
          <tbody>
            @for (h of r.horarios; track h.id) {
              <tr><td>{{ h.dia_nombre }}</td><td>{{ h.hora_inicio.slice(0, 5) }}</td><td>{{ h.hora_fin.slice(0, 5) }}</td></tr>
            }
          </tbody>
        </table>
        <p><b>Paradas:</b>
          @for (p of r.puntos; track p.id) { <span>{{ p.orden }}. {{ p.referencia }}{{ $last ? '' : ' → ' }}</span> }
        </p>
      </div>
    } @empty { <div class="tarjeta">No hay rutas registradas.</div> }
  `,
})
export class RutasComponent implements OnInit {
  private api = inject(ApiService);
  rutas: Ruta[] = [];
  ngOnInit(): void { this.api.rutas().subscribe(r => (this.rutas = r)); }
}

```

## Angular: camiones
`frontend/src/app/pages/camiones.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { Camion } from '../models/models';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-camiones',
  standalone: true,
  template: `
    <div class="tarjeta">
      <h2>Flota de camiones</h2>
      <table>
        <thead><tr><th>Código</th><th>Placa</th><th>Operador</th><th>Capacidad</th><th>Estado</th><th>Última posición</th></tr></thead>
        <tbody>
          @for (c of camiones; track c.id) {
            <tr>
              <td>{{ c.codigo }}</td><td>{{ c.placa }}</td><td>{{ c.operador_nombre ?? '—' }}</td>
              <td>{{ c.capacidad_kg }} kg</td>
              <td><span [class]="'etiqueta ' + c.estado">{{ c.estado }}</span></td>
              <td>
                @if (c.ultima_posicion) { {{ c.ultima_posicion.latitud }}, {{ c.ultima_posicion.longitud }} }
                @else { sin datos }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
})
export class CamionesComponent implements OnInit {
  private api = inject(ApiService);
  camiones: Camion[] = [];
  ngOnInit(): void { this.api.camiones().subscribe(c => (this.camiones = c)); }
}

```
