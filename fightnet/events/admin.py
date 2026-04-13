"""
admin.py - Panel administrativo de Fight.net
Modelos registrados con list_display, search_fields, list_filter,
readonly_fields, inlines y personalizacion del sitio.
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Event, EventRegistration, Comment, EventCreationLog


# ══════════════════════════════════════════════
# Personalizacion del sitio de administracion
# ══════════════════════════════════════════════

admin.site.site_header  = "Fight.net - Administracion"
admin.site.site_title   = "Fight.net Admin"
admin.site.index_title  = "Panel de Control"


# ══════════════════════════════════════════════
# INLINE: UserProfile dentro del admin de User
# Permite ver y editar el perfil directamente
# desde la pagina del usuario en el admin.
# ══════════════════════════════════════════════

class UserProfileInline(admin.StackedInline):
    model          = UserProfile
    can_delete     = False
    verbose_name_plural = 'Perfil'
    fields         = ('rol', 'bio')
    extra          = 0


class UserAdmin(BaseUserAdmin):
    inlines        = (UserProfileInline,)
    list_display   = ('username', 'email', 'get_rol', 'is_staff', 'is_active', 'date_joined')
    list_filter    = ('is_staff', 'is_active', 'profile__rol')
    search_fields  = ('username', 'email', 'first_name', 'last_name')
    ordering       = ('-date_joined',)

    def get_rol(self, obj):
        perfil = getattr(obj, 'profile', None)
        return perfil.get_rol_display() if perfil else '—'
    get_rol.short_description = 'Rol'

# Reemplaza el UserAdmin por defecto para incluir el inline
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# ══════════════════════════════════════════════
# TABLA 1: Perfil de usuario
# ══════════════════════════════════════════════

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display        = ('user', 'get_email', 'rol', 'tiene_bio')
    list_display_links  = ('user',)
    search_fields       = ('user__username', 'user__email', 'bio')
    list_filter         = ('rol',)
    readonly_fields     = ('user',)
    ordering            = ('rol', 'user__username')
    fieldsets           = (
        ('Informacion de cuenta', {
            'fields': ('user', 'rol')
        }),
        ('Informacion adicional', {
            'fields': ('bio',),
            'classes': ('collapse',),
        }),
    )

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def tiene_bio(self, obj):
        return bool(obj.bio)
    tiene_bio.short_description = 'Tiene bio'
    tiene_bio.boolean = True


# ══════════════════════════════════════════════
# TABLA 2: Eventos
# ══════════════════════════════════════════════

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display        = ('titulo', 'creador', 'fecha', 'ubicacion', 'estado', 'total_registros', 'fecha_creacion')
    list_display_links  = ('titulo',)
    search_fields       = ('titulo', 'descripcion', 'ubicacion', 'creador__username')
    list_filter         = ('estado',)
    readonly_fields     = ('fecha_creacion', 'total_registros')
    date_hierarchy      = 'fecha'
    ordering            = ('-fecha',)
    list_per_page       = 20
    fieldsets           = (
        ('Informacion del evento', {
            'fields': ('titulo', 'descripcion', 'creador')
        }),
        ('Fecha y lugar', {
            'fields': ('fecha', 'ubicacion')
        }),
        ('Estado y auditoria', {
            'fields': ('estado', 'fecha_creacion', 'total_registros'),
        }),
    )

    def total_registros(self, obj):
        return obj.registros.count()
    total_registros.short_description = 'Registros'


# ══════════════════════════════════════════════
# TABLA 3: Registros a eventos
# ══════════════════════════════════════════════

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display        = ('usuario', 'evento', 'estado', 'check_in', 'fecha_registro', 'codigo_qr_corto')
    list_display_links  = ('usuario',)
    search_fields       = ('usuario__username', 'evento__titulo', 'codigo_qr')
    list_filter         = ('estado', 'check_in', 'fecha_registro')
    readonly_fields     = ('codigo_qr', 'imagen_qr', 'fecha_registro')
    date_hierarchy      = 'fecha_registro'
    ordering            = ('-fecha_registro',)
    list_per_page       = 25
    fieldsets           = (
        ('Informacion del registro', {
            'fields': ('usuario', 'evento', 'estado', 'check_in')
        }),
        ('Codigo QR', {
            'fields': ('codigo_qr', 'imagen_qr'),
            'classes': ('collapse',),
        }),
        ('Fechas', {
            'fields': ('fecha_registro',),
        }),
    )

    def codigo_qr_corto(self, obj):
        return obj.codigo_qr[:8] + '...' if obj.codigo_qr else '—'
    codigo_qr_corto.short_description = 'QR (corto)'


# ══════════════════════════════════════════════
# TABLA 4: Comentarios
# ══════════════════════════════════════════════

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display        = ('usuario', 'evento', 'contenido_corto', 'fecha_comentario')
    list_display_links  = ('usuario',)
    search_fields       = ('usuario__username', 'evento__titulo', 'contenido')
    list_filter         = ('fecha_comentario', 'evento')
    readonly_fields     = ('fecha_comentario',)
    date_hierarchy      = 'fecha_comentario'
    ordering            = ('-fecha_comentario',)
    list_per_page       = 25

    def contenido_corto(self, obj):
        return obj.contenido[:60] + '...' if len(obj.contenido) > 60 else obj.contenido
    contenido_corto.short_description = 'Contenido'


# ══════════════════════════════════════════════
# TABLA 5: Log de creacion de eventos
# ══════════════════════════════════════════════

@admin.register(EventCreationLog)
class EventCreationLogAdmin(admin.ModelAdmin):
    list_display        = ('evento', 'creador', 'estatus', 'fecha_creacion')
    list_display_links  = ('evento',)
    search_fields       = ('evento__titulo', 'creador__username')
    list_filter         = ('estatus', 'fecha_creacion')
    readonly_fields     = ('evento', 'creador', 'fecha_creacion')
    date_hierarchy      = 'fecha_creacion'
    ordering            = ('-fecha_creacion',)
    list_per_page       = 20
    fieldsets           = (
        ('Evento auditado', {
            'fields': ('evento', 'creador', 'fecha_creacion')
        }),
        ('Resultado', {
            'fields': ('estatus',),
        }),
    )