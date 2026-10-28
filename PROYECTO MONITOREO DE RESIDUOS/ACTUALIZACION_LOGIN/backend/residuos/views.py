from django.contrib.auth import authenticate
from django.db.models import OuterRef, Subquery
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (Camion, Horario, Incidencia, PosicionGPS, PuntoRuta,
                     RecorridoRealizado, Ruta, Sector)
from .serializers import (CamionSerializer, HorarioSerializer, IncidenciaSerializer,
                          PosicionGPSSerializer, PuntoRutaSerializer, RecorridoSerializer,
                          RutaSerializer, SectorSerializer, UsuarioSerializer)
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


class LoginView(APIView):
    """POST {username, password} -> {token, usuario}. Es la única ruta pública."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        usuario = authenticate(username=request.data.get("username"),
                               password=request.data.get("password"))
        if usuario is None:
            return Response({"detail": "Usuario o contraseña incorrectos"},
                            status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=usuario)
        return Response({"token": token.key, "usuario": UsuarioSerializer(usuario).data})


class LogoutView(APIView):
    """POST -> elimina el token del usuario (cierra sesión)."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
