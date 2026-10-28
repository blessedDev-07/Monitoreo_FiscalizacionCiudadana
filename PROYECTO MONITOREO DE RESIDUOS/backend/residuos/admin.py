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
