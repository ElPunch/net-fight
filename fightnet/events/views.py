"""
views.py – Vistas de Fight.net
Todo con Function-Based Views (FBV) y respuestas JSON simples.
Sin Django REST Framework: usamos JsonResponse directamente.
"""

import uuid
import json
import qrcode
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .models import Event, EventRegistration, Comment, UserProfile, EventCreationLog


# ══════════════════════════════════════════════
# VISTAS DE PÁGINA (renderizan HTML)
# ══════════════════════════════════════════════

def login_view(request):
    """Página de inicio de sesión."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': 'Credenciales incorrectas'}, status=400)

    return render(request, 'events/login.html')


def register_view(request):
    """Registro de nuevo usuario."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email    = data.get('email', '').strip()
        password = data.get('password', '')
        rol      = data.get('rol', 'fighter')

        if User.objects.filter(username=username).exists():
            return JsonResponse({'ok': False, 'error': 'El usuario ya existe'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, rol=rol)
        login(request, user)
        return JsonResponse({'ok': True})

    return render(request, 'events/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def index(request):
    """Página principal con listado de eventos."""
    return render(request, 'events/index.html')


@login_required
def event_detail(request, pk):
    """Detalle de un evento: asistentes y comentarios."""
    return render(request, 'events/event_detail.html', {'event_id': pk})


@login_required
def my_qr(request, registration_id):
    """Página que muestra el QR del usuario para un evento."""
    reg = get_object_or_404(EventRegistration, pk=registration_id, usuario=request.user)
    return render(request, 'events/my_qr.html', {'registration': reg})


# ══════════════════════════════════════════════
# API JSON – Eventos
# ══════════════════════════════════════════════

@login_required
def api_events(request):
    """
    GET  /api/events/  → lista todos los eventos activos
    POST /api/events/  → crea un nuevo evento
    """
    if request.method == 'GET':
        events = Event.objects.filter(estado='activo').select_related('creador')
        data = [
            {
                'id':          e.id,
                'titulo':      e.titulo,
                'descripcion': e.descripcion,
                'fecha':       e.fecha.strftime('%d/%m/%Y %H:%M'),
                'ubicacion':   e.ubicacion,
                'estado':      e.estado,
                'creador':     e.creador.username,
            }
            for e in events
        ]
        return JsonResponse({'events': data})

    if request.method == 'POST':
        data = json.loads(request.body)
        event = Event.objects.create(
            titulo      = data['titulo'],
            descripcion = data['descripcion'],
            fecha       = data['fecha'],       # formato ISO: "2025-06-15T18:00"
            ubicacion   = data['ubicacion'],
            creador     = request.user,
        )
        # Creamos el log de auditoría automáticamente
        EventCreationLog.objects.create(evento=event, creador=request.user, estatus='aprobado')
        return JsonResponse({'ok': True, 'id': event.id}, status=201)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def api_event_detail(request, pk):
    """
    GET    /api/events/<pk>/  → detalle de un evento
    DELETE /api/events/<pk>/  → elimina un evento (solo su creador o admin)
    """
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'GET':
        return JsonResponse({
            'id':          event.id,
            'titulo':      event.titulo,
            'descripcion': event.descripcion,
            'fecha':       event.fecha.strftime('%d/%m/%Y %H:%M'),
            'ubicacion':   event.ubicacion,
            'estado':      event.estado,
            'creador':     event.creador.username,
        })

    if request.method == 'DELETE':
        if event.creador != request.user and not request.user.is_staff:
            return JsonResponse({'error': 'Sin permiso'}, status=403)
        event.delete()
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ══════════════════════════════════════════════
# API JSON – Registro a eventos
# ══════════════════════════════════════════════

def _generar_qr(codigo, filename):
    """Función auxiliar: genera imagen QR y la guarda en MEDIA_ROOT/qrcodes/."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(codigo)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
    os.makedirs(qr_dir, exist_ok=True)

    ruta = os.path.join(qr_dir, filename)
    img.save(ruta)
    return f'qrcodes/{filename}'


@login_required
def api_register_event(request):
    """
    POST /api/register-event/
    Body: { "evento_id": 1 }
    Crea un registro y genera el QR.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data     = json.loads(request.body)
    event    = get_object_or_404(Event, pk=data['evento_id'])

    if EventRegistration.objects.filter(usuario=request.user, evento=event).exists():
        return JsonResponse({'ok': False, 'error': 'Ya estás registrado en este evento'}, status=400)

    # Código único para el QR
    codigo = str(uuid.uuid4())
    filename = f'{codigo}.png'
    ruta_imagen = _generar_qr(codigo, filename)

    reg = EventRegistration.objects.create(
        usuario   = request.user,
        evento    = event,
        codigo_qr = codigo,
        imagen_qr = ruta_imagen,
    )
    return JsonResponse({'ok': True, 'registration_id': reg.id, 'codigo_qr': codigo}, status=201)


@login_required
def api_attendees(request, pk):
    """
    GET /api/event-attendees/<pk>/
    Devuelve la lista de asistentes de un evento.
    """
    event = get_object_or_404(Event, pk=pk)
    registros = EventRegistration.objects.filter(evento=event).select_related('usuario')
    data = [
        {
            'usuario':  r.usuario.username,
            'estado':   r.estado,
            'check_in': r.check_in,
        }
        for r in registros
    ]
    return JsonResponse({'attendees': data, 'total': len(data)})


# ══════════════════════════════════════════════
# API JSON – Comentarios
# ══════════════════════════════════════════════

@login_required
def api_comments(request, pk):
    """
    GET  /api/event-comments/<pk>/  → lista comentarios
    POST /api/event-comment/<pk>/   → agrega comentario
    """
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'GET':
        comments = Comment.objects.filter(evento=event).select_related('usuario')
        data = [
            {
                'usuario': c.usuario.username,
                'contenido': c.contenido,
                'fecha': c.fecha_comentario.strftime('%d/%m/%Y %H:%M'),
            }
            for c in comments
        ]
        return JsonResponse({'comments': data})

    if request.method == 'POST':
        data = json.loads(request.body)
        Comment.objects.create(
            evento   = event,
            usuario  = request.user,
            contenido = data['contenido'],
        )
        return JsonResponse({'ok': True}, status=201)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ══════════════════════════════════════════════
# API JSON – Check-in por QR
# ══════════════════════════════════════════════

@login_required
def api_checkin(request):
    """
    POST /api/check-in/
    Body: { "codigo_qr": "<uuid>" }
    Valida el código QR y marca check_in = True.
    Solo el creador del evento o staff pueden hacer check-in.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data   = json.loads(request.body)
    codigo = data.get('codigo_qr', '')

    try:
        reg = EventRegistration.objects.select_related('evento', 'usuario').get(codigo_qr=codigo)
    except EventRegistration.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Código QR inválido'}, status=404)

    if reg.check_in:
        return JsonResponse({'ok': False, 'error': 'Ya se realizó el check-in'}, status=400)

    reg.check_in = True
    reg.estado   = 'confirmado'
    reg.save()

    return JsonResponse({
        'ok':      True,
        'usuario': reg.usuario.username,
        'evento':  reg.evento.titulo,
    })


# ══════════════════════════════════════════════
# API – Info del usuario actual
# ══════════════════════════════════════════════

@login_required
def api_me(request):
    """Devuelve datos básicos del usuario autenticado."""
    perfil = getattr(request.user, 'profile', None)
    return JsonResponse({
        'username': request.user.username,
        'email':    request.user.email,
        'rol':      perfil.rol if perfil else 'fighter',
    })
