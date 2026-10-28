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
