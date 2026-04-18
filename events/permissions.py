"""
permissions.py - Permisos personalizados de DRF para Fight.net
"""

from rest_framework import permissions


def _get_rol(user):
    perfil = getattr(user, 'profile', None)
    return perfil.rol if perfil else None


class IsPromoter(permissions.BasePermission):
    """Solo los usuarios con rol 'promoter' pueden acceder."""
    message = 'Se requiere el rol de promotor para realizar esta accion.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_rol(request.user) == 'promoter'


class IsFighter(permissions.BasePermission):
    """Solo los usuarios con rol 'fighter' pueden acceder."""
    message = 'Se requiere el rol de peleador para realizar esta accion.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and _get_rol(request.user) == 'fighter'


class IsEventCreatorOrReadOnly(permissions.BasePermission):
    """Permite modificar/eliminar un evento solo a su creador (o staff)."""
    message = 'Solo el promotor creador puede modificar este evento.'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.creador_id == request.user.id or request.user.is_staff


class ReadOnly(permissions.BasePermission):
    """Solo permite metodos de lectura (GET/HEAD/OPTIONS)."""

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
