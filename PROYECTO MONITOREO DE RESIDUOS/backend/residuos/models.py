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
