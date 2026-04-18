"""
api_views.py - Vistas de la API (Django Rest Framework) para Fight.net

Cada recurso expone solamente los metodos HTTP que tienen sentido para el
negocio. Esto cumple con el requerimiento de restringir los metodos por
endpoint (por ejemplo, la lista de peleadores solo permite GET).
"""

import os
import uuid
import qrcode

from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework import generics, status, viewsets, mixins, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Event,
    EventRegistration,
    Comment,
    Fight,
    UserProfile,
    EventCreationLog,
)
from .serializers import (
    EventSerializer,
    EventRegistrationSerializer,
    CommentSerializer,
    FightSerializer,
    UserProfileSerializer,
    UserSerializer,
    FighterBriefSerializer,
    EventCreationLogSerializer,
)
from .permissions import (
    IsPromoter,
    IsFighter,
    IsEventCreatorOrReadOnly,
)


# ══════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════

def _get_rol(user):
    perfil = getattr(user, 'profile', None)
    return perfil.rol if perfil else 'fighter'


def _generar_qr(codigo, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(codigo)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)

    ruta = os.path.join(qr_dir, filename)
    img.save(ruta)
    return f'qrcodes/{filename}'


# ══════════════════════════════════════════════
# Eventos - ViewSet completo
# GET, POST, PUT/PATCH, DELETE  (POST y DELETE con restricciones de rol)
# ══════════════════════════════════════════════

class EventViewSet(viewsets.ModelViewSet):
    """
    Endpoints:
      - GET    /api/events/          -> lista de eventos activos
      - POST   /api/events/          -> crear evento + enfrentamientos (solo promotor)
      - GET    /api/events/{id}/     -> detalle de evento (incluye cartelera)
      - PUT    /api/events/{id}/     -> editar evento (solo creador)
      - PATCH  /api/events/{id}/     -> editar parcial (solo creador)
      - DELETE /api/events/{id}/     -> eliminar evento (solo creador/staff)
    """
    serializer_class   = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsEventCreatorOrReadOnly]

    def get_queryset(self):
        qs = Event.objects.all().select_related('creador').prefetch_related(
            'enfrentamientos__peleador_a__profile',
            'enfrentamientos__peleador_b__profile',
            'registros',
        )
        # En la lista solo eventos activos; en el detalle se permite cualquiera
        if self.action == 'list':
            qs = qs.filter(estado='activo')
        return qs

    def get_permissions(self):
        # Crear: solo promotores
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsPromoter()]
        return super().get_permissions()


# ══════════════════════════════════════════════
# "Mis eventos" - solo lectura para el promotor
# GET unicamente
# ══════════════════════════════════════════════

class MisEventosListView(generics.ListAPIView):
    serializer_class   = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsPromoter]

    def get_queryset(self):
        return (Event.objects
                .filter(creador=self.request.user)
                .order_by('-fecha_creacion')
                .prefetch_related('enfrentamientos', 'registros'))


# ══════════════════════════════════════════════
# Peleadores disponibles (solo lectura)
# GET unicamente -> usado en el modal de creacion de evento
# ══════════════════════════════════════════════

class FighterListView(generics.ListAPIView):
    """GET /api/fighters/ -> lista de usuarios con rol peleador."""
    serializer_class   = FighterBriefSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'head', 'options']

    def get_queryset(self):
        return (UserProfile.objects
                .filter(rol='fighter')
                .select_related('user')
                .order_by('user__username'))


# ══════════════════════════════════════════════
# Enfrentamientos
# Lectura publica para participantes autenticados,
# creacion/edicion solo para el promotor del evento.
# ══════════════════════════════════════════════

class EventFightsView(generics.ListCreateAPIView):
    """
    GET  /api/events/{pk}/fights/  -> lista de enfrentamientos del evento
    POST /api/events/{pk}/fights/  -> agregar un enfrentamiento (solo promotor creador)
    """
    serializer_class   = FightSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_event(self):
        return get_object_or_404(Event, pk=self.kwargs['pk'])

    def get_queryset(self):
        return (Fight.objects
                .filter(evento_id=self.kwargs['pk'])
                .select_related('peleador_a__profile', 'peleador_b__profile')
                .order_by('orden'))

    def create(self, request, *args, **kwargs):
        event = self.get_event()
        if event.creador_id != request.user.id and not request.user.is_staff:
            return Response(
                {'detail': 'Solo el promotor creador puede agregar enfrentamientos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(evento=event)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FightDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/fights/{id}/
    PUT    /api/fights/{id}/
    PATCH  /api/fights/{id}/
    DELETE /api/fights/{id}/
    """
    serializer_class   = FightSerializer
    queryset           = Fight.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def check_owner(self, fight):
        if fight.evento.creador_id != self.request.user.id and not self.request.user.is_staff:
            return False
        return True

    def update(self, request, *args, **kwargs):
        fight = self.get_object()
        if not self.check_owner(fight):
            return Response(
                {'detail': 'Solo el promotor del evento puede modificar este enfrentamiento.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        fight = self.get_object()
        if not self.check_owner(fight):
            return Response(
                {'detail': 'Solo el promotor del evento puede eliminar este enfrentamiento.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


# ══════════════════════════════════════════════
# Registros (asistentes a evento)
# GET de asistentes, POST para registrarse (solo peleadores)
# ══════════════════════════════════════════════

class EventAttendeesView(generics.ListAPIView):
    """GET /api/events/{pk}/attendees/ -> lista de asistentes del evento."""
    serializer_class   = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'head', 'options']

    def get_queryset(self):
        return (EventRegistration.objects
                .filter(evento_id=self.kwargs['pk'])
                .select_related('usuario', 'usuario__profile'))


class RegisterToEventView(generics.CreateAPIView):
    """POST /api/register-event/ -> registra al peleador al evento."""
    serializer_class   = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated, IsFighter]
    http_method_names  = ['post', 'options']

    def create(self, request, *args, **kwargs):
        evento_id = request.data.get('evento_id') or request.data.get('evento')
        if not evento_id:
            return Response({'detail': 'Falta evento_id'}, status=400)

        event = get_object_or_404(Event, pk=evento_id)
        if EventRegistration.objects.filter(usuario=request.user, evento=event).exists():
            return Response(
                {'detail': 'Ya estas registrado en este evento.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        codigo      = str(uuid.uuid4())
        filename    = f'{codigo}.png'
        ruta_imagen = _generar_qr(codigo, filename)

        reg = EventRegistration.objects.create(
            usuario   = request.user,
            evento    = event,
            codigo_qr = codigo,
            imagen_qr = ruta_imagen,
        )
        return Response(
            {'ok': True, 'registration_id': reg.id, 'codigo_qr': codigo},
            status=status.HTTP_201_CREATED,
        )


class MyRegistrationView(generics.RetrieveAPIView):
    """GET /api/my-registration/{pk}/ -> estado del usuario para ese evento."""
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'head', 'options']

    def retrieve(self, request, pk, *args, **kwargs):
        try:
            reg = EventRegistration.objects.get(usuario=request.user, evento_id=pk)
            return Response({
                'registered':      True,
                'registration_id': reg.id,
                'codigo_qr':       reg.codigo_qr,
            })
        except EventRegistration.DoesNotExist:
            return Response({'registered': False})


# ══════════════════════════════════════════════
# Comentarios
# GET y POST (no se permite eliminar desde la API)
# ══════════════════════════════════════════════

class EventCommentsView(generics.ListCreateAPIView):
    """
    GET  /api/events/{pk}/comments/  -> lista comentarios del evento
    POST /api/events/{pk}/comments/  -> crear comentario
    """
    serializer_class   = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (Comment.objects
                .filter(evento_id=self.kwargs['pk'])
                .select_related('usuario'))

    def perform_create(self, serializer):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])
        serializer.save(usuario=self.request.user, evento=event)


# ══════════════════════════════════════════════
# Check-in
# POST unicamente
# ══════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsPromoter])
def api_checkin(request):
    """POST /api/check-in/ -> body: {codigo_qr}"""
    codigo = request.data.get('codigo_qr', '')
    if not codigo:
        return Response({'ok': False, 'detail': 'Falta codigo_qr'}, status=400)

    try:
        reg = EventRegistration.objects.select_related('evento', 'usuario').get(codigo_qr=codigo)
    except EventRegistration.DoesNotExist:
        return Response({'ok': False, 'detail': 'Codigo QR invalido'}, status=404)

    if reg.evento.creador != request.user and not request.user.is_staff:
        return Response(
            {'ok': False, 'detail': 'Solo el promotor del evento puede hacer check-in.'},
            status=403,
        )

    if reg.check_in:
        return Response({'ok': False, 'detail': 'Ya se realizo el check-in.'}, status=400)

    reg.check_in = True
    reg.estado   = 'confirmado'
    reg.save()
    return Response({'ok': True, 'usuario': reg.usuario.username, 'evento': reg.evento.titulo})


# ══════════════════════════════════════════════
# Perfil del usuario actual
# GET y POST (para editar)
# ══════════════════════════════════════════════

class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/me/      -> datos del perfil
    PUT  /api/me/      -> actualizar perfil (solo peleadores)
    PATCH /api/me/     -> actualizar parcial
    """
    serializer_class   = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names  = ['get', 'put', 'patch', 'post', 'head', 'options']

    def get_object(self):
        perfil, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return perfil

    def post(self, request, *args, **kwargs):
        # Mantiene compatibilidad con el frontend existente que usa POST.
        return self.partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if _get_rol(request.user) != 'fighter':
            return Response(
                {'detail': 'Solo los peleadores pueden editar su perfil.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)


# ══════════════════════════════════════════════
# Log de auditoria - solo GET (read-only)
# ══════════════════════════════════════════════

class EventCreationLogViewSet(mixins.ListModelMixin,
                              mixins.RetrieveModelMixin,
                              viewsets.GenericViewSet):
    """
    Demostracion de endpoint de SOLO LECTURA:
    GET /api/logs/        -> lista
    GET /api/logs/{id}/   -> detalle
    (No se permiten POST/PUT/PATCH/DELETE).
    """
    queryset           = EventCreationLog.objects.select_related('evento', 'creador').all()
    serializer_class   = EventCreationLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsPromoter]
