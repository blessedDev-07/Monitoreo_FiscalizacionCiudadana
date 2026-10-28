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
