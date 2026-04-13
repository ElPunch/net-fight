"""
admin.py – Panel administrativo de Fight.net
Todos los modelos registrados con list_display, search_fields y list_filter.
"""

from django.contrib import admin
from .models import UserProfile, Event, EventRegistration, Comment, EventCreationLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rol", "disciplina", "peso", "edad", "user__email")
    search_fields = ("user__username", "user__email")
    list_filter = ("rol", "disciplina")
    readonly_fields = ("foto",)

    def user__email(self, obj):
        return obj.user.email

    user__email.short_description = "Email"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "fecha",
        "ubicacion",
        "estado",
        "creador",
        "fecha_creacion",
    )
    search_fields = ("titulo", "descripcion", "ubicacion", "creador__username")
    list_filter = ("estado", "fecha")
    date_hierarchy = "fecha"


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento", "estado", "check_in", "fecha_registro")
    search_fields = ("usuario__username", "evento__titulo", "codigo_qr")
    list_filter = ("estado", "check_in")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento", "fecha_comentario")
    search_fields = ("usuario__username", "evento__titulo", "contenido")
    list_filter = ("fecha_comentario",)


@admin.register(EventCreationLog)
class EventCreationLogAdmin(admin.ModelAdmin):
    list_display = ("evento", "creador", "estatus", "fecha_creacion")
    search_fields = ("evento__titulo", "creador__username")
    list_filter = ("estatus",)
