"""
views.py - Vistas de Fight.net
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
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.conf import settings

from .models import Event, EventRegistration, Comment, UserProfile, EventCreationLog


# ══════════════════════════════════════════════
# HELPER: obtener rol del usuario
# ══════════════════════════════════════════════

def get_rol(user):
    perfil = getattr(user, 'profile', None)
    return perfil.rol if perfil else 'fighter'


# ══════════════════════════════════════════════
# VISTAS DE PAGINA
# ══════════════════════════════════════════════

@ensure_csrf_cookie
@csrf_exempt
def login_view(request):
    if request.user.is_authenticated and request.method == 'GET':
        return _redirect_by_rol(request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Datos invalidos'}, status=400)

        username = data.get('username', '').strip()
        password = data.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            rol = get_rol(user)
            redirect_url = '/promotor/' if rol == 'promoter' else '/peleador/'
            return JsonResponse({'ok': True, 'rol': rol, 'redirect': redirect_url})
        return JsonResponse({'ok': False, 'error': 'Credenciales incorrectas'}, status=400)

    return render(request, 'events/login.html')


@ensure_csrf_cookie
@csrf_exempt
def register_view(request):
    if request.user.is_authenticated and request.method == 'GET':
        return _redirect_by_rol(request.user)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Datos invalidos'}, status=400)

        username = data.get('username', '').strip()
        email    = data.get('email', '').strip()
        password = data.get('password', '')
        rol      = data.get('rol', 'fighter')

        if rol not in ('fighter', 'promoter'):
            rol = 'fighter'

        if not username or not password:
            return JsonResponse({'ok': False, 'error': 'Usuario y contrasena son requeridos'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'ok': False, 'error': 'El usuario ya existe'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user, rol=rol)
        login(request, user)

        redirect_url = '/promotor/' if rol == 'promoter' else '/peleador/'
        return JsonResponse({'ok': True, 'rol': rol, 'redirect': redirect_url})

    return render(request, 'events/register.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def _redirect_by_rol(user):
    rol = get_rol(user)
    if rol == 'promoter':
        return redirect('dashboard_promotor')
    return redirect('dashboard_peleador')


@login_required
def index(request):
    return _redirect_by_rol(request.user)


@login_required
def dashboard_promotor(request):
    if get_rol(request.user) != 'promoter':
        return redirect('dashboard_peleador')
    return render(request, 'events/index_promotor.html')


@login_required
def dashboard_peleador(request):
    if get_rol(request.user) != 'fighter':
        return redirect('dashboard_promotor')
    return render(request, 'events/index_peleador.html')


@login_required
def perfil_view(request):
    if get_rol(request.user) != 'fighter':
        return redirect('dashboard_promotor')
    return render(request, 'events/perfil.html')


@login_required
def event_detail(request, pk):
    return render(request, 'events/event_detail.html', {'event_id': pk})


@login_required
def my_qr(request, registration_id):
    reg = get_object_or_404(EventRegistration, pk=registration_id, usuario=request.user)
    return render(request, 'events/my_qr.html', {'registration': reg})


# ══════════════════════════════════════════════
# API JSON - Eventos
# ══════════════════════════════════════════════

@login_required
def api_events(request):
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
        if get_rol(request.user) != 'promoter':
            return JsonResponse({'error': 'Solo los promotores pueden crear eventos'}, status=403)

        data  = json.loads(request.body)
        event = Event.objects.create(
            titulo      = data['titulo'],
            descripcion = data['descripcion'],
            fecha       = data['fecha'],
            ubicacion   = data['ubicacion'],
            creador     = request.user,
        )
        EventCreationLog.objects.create(evento=event, creador=request.user, estatus='aprobado')
        return JsonResponse({'ok': True, 'id': event.id}, status=201)

    return JsonResponse({'error': 'Metodo no permitido'}, status=405)


@login_required
def api_mis_eventos(request):
    if get_rol(request.user) != 'promoter':
        return JsonResponse({'error': 'Sin permiso'}, status=403)

    events = Event.objects.filter(creador=request.user).order_by('-fecha_creacion')
    data = [
        {
            'id':          e.id,
            'titulo':      e.titulo,
            'descripcion': e.descripcion,
            'fecha':       e.fecha.strftime('%d/%m/%Y %H:%M'),
            'ubicacion':   e.ubicacion,
            'estado':      e.estado,
            'total_registros': e.registros.count(),
        }
        for e in events
    ]
    return JsonResponse({'events': data})


@login_required
def api_event_detail(request, pk):
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

    return JsonResponse({'error': 'Metodo no permitido'}, status=405)


# ══════════════════════════════════════════════
# API JSON - Registro a eventos
# ══════════════════════════════════════════════

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


@login_required
def api_register_event(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido'}, status=405)

    if get_rol(request.user) == 'promoter':
        return JsonResponse({'error': 'Los promotores no pueden registrarse como asistentes'}, status=403)

    data  = json.loads(request.body)
    event = get_object_or_404(Event, pk=data['evento_id'])

    if EventRegistration.objects.filter(usuario=request.user, evento=event).exists():
        return JsonResponse({'ok': False, 'error': 'Ya estas registrado en este evento'}, status=400)

    codigo      = str(uuid.uuid4())
    filename    = f'{codigo}.png'
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
    event     = get_object_or_404(Event, pk=pk)
    registros = EventRegistration.objects.filter(evento=event).select_related(
        'usuario', 'usuario__profile'
    )
    data = []
    for r in registros:
        perfil = getattr(r.usuario, 'profile', None)
        data.append({
            'usuario':     r.usuario.username,
            'estado':      r.estado,
            'check_in':    r.check_in,
            'foto_perfil': perfil.foto_url if perfil else None,
            'disciplina':  perfil.get_disciplina_display() if perfil and perfil.disciplina else None,
            'categoria':   perfil.categoria if perfil else None,
        })
    return JsonResponse({'attendees': data, 'total': len(data)})


@login_required
def api_my_registration(request, pk):
    try:
        reg = EventRegistration.objects.get(usuario=request.user, evento_id=pk)
        return JsonResponse({'registered': True, 'registration_id': reg.id, 'codigo_qr': reg.codigo_qr})
    except EventRegistration.DoesNotExist:
        return JsonResponse({'registered': False})


# ══════════════════════════════════════════════
# API JSON - Comentarios
# ══════════════════════════════════════════════

@login_required
def api_comments(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'GET':
        comments = Comment.objects.filter(evento=event).select_related('usuario')
        data = [
            {
                'usuario':   c.usuario.username,
                'contenido': c.contenido,
                'fecha':     c.fecha_comentario.strftime('%d/%m/%Y %H:%M'),
            }
            for c in comments
        ]
        return JsonResponse({'comments': data})

    if request.method == 'POST':
        data = json.loads(request.body)
        Comment.objects.create(
            evento    = event,
            usuario   = request.user,
            contenido = data['contenido'],
        )
        return JsonResponse({'ok': True}, status=201)

    return JsonResponse({'error': 'Metodo no permitido'}, status=405)


# ══════════════════════════════════════════════
# API JSON - Check-in por QR
# ══════════════════════════════════════════════

@login_required
def api_checkin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido'}, status=405)

    data   = json.loads(request.body)
    codigo = data.get('codigo_qr', '')

    try:
        reg = EventRegistration.objects.select_related('evento', 'usuario').get(codigo_qr=codigo)
    except EventRegistration.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Codigo QR invalido'}, status=404)

    if reg.evento.creador != request.user and not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'Solo el promotor del evento puede hacer check-in'}, status=403)

    if reg.check_in:
        return JsonResponse({'ok': False, 'error': 'Ya se realizo el check-in'}, status=400)

    reg.check_in = True
    reg.estado   = 'confirmado'
    reg.save()

    return JsonResponse({
        'ok':      True,
        'usuario': reg.usuario.username,
        'evento':  reg.evento.titulo,
    })


# ══════════════════════════════════════════════
# API - Info y edicion del usuario actual
# ══════════════════════════════════════════════

@login_required
def api_me(request):
    perfil = getattr(request.user, 'profile', None)

    if request.method == 'GET':
        return JsonResponse({
            'username':    request.user.username,
            'email':       request.user.email,
            'rol':         perfil.rol if perfil else 'fighter',
            'bio':         perfil.bio or '',
            'foto_perfil': perfil.foto_url if perfil else None,
            'disciplina':  perfil.disciplina or '',
            'categoria':   perfil.categoria or '',
            'peso_kg':     str(perfil.peso_kg) if perfil and perfil.peso_kg else '',
            'estatura_cm': perfil.estatura_cm or '',
            'edad':        perfil.edad or '',
            'victorias':   perfil.victorias if perfil else 0,
            'derrotas':    perfil.derrotas if perfil else 0,
            'empates':     perfil.empates if perfil else 0,
        })

    # POST: acepta multipart (con foto) o JSON (sin foto)
    if request.method == 'POST':
        if get_rol(request.user) != 'fighter':
            return JsonResponse({'error': 'Solo los peleadores pueden editar su perfil'}, status=403)

        # Detectar si viene como multipart/form-data (con foto) o JSON
        content_type = request.content_type or ''
        if 'multipart' in content_type:
            data = request.POST
            foto = request.FILES.get('foto_perfil')
        else:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Datos invalidos'}, status=400)
            foto = None

        # Actualizar User
        email = data.get('email', '').strip()
        if email:
            request.user.email = email
            request.user.save()

        # Actualizar perfil
        if perfil:
            if data.get('bio') is not None:
                perfil.bio = data.get('bio', '').strip()
            if data.get('disciplina') is not None:
                perfil.disciplina = data.get('disciplina', '') or None
            if data.get('categoria') is not None:
                perfil.categoria = data.get('categoria', '').strip() or None
            if data.get('peso_kg') is not None:
                try:
                    perfil.peso_kg = float(data.get('peso_kg')) if data.get('peso_kg') else None
                except (ValueError, TypeError):
                    perfil.peso_kg = None
            if data.get('estatura_cm') is not None:
                try:
                    perfil.estatura_cm = int(data.get('estatura_cm')) if data.get('estatura_cm') else None
                except (ValueError, TypeError):
                    perfil.estatura_cm = None
            if data.get('edad') is not None:
                try:
                    perfil.edad = int(data.get('edad')) if data.get('edad') else None
                except (ValueError, TypeError):
                    perfil.edad = None
            if data.get('victorias') is not None:
                try:
                    perfil.victorias = int(data.get('victorias', 0))
                except (ValueError, TypeError):
                    pass
            if data.get('derrotas') is not None:
                try:
                    perfil.derrotas = int(data.get('derrotas', 0))
                except (ValueError, TypeError):
                    pass
            if data.get('empates') is not None:
                try:
                    perfil.empates = int(data.get('empates', 0))
                except (ValueError, TypeError):
                    pass
            if foto:
                perfil.foto_perfil = foto
            perfil.save()

        return JsonResponse({'ok': True, 'foto_perfil': perfil.foto_url if perfil else None})

    return JsonResponse({'error': 'Metodo no permitido'}, status=405)
