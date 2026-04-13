"""
views.py - Vistas de Fight.net
FBV con JsonResponse. Sin Django REST Framework.
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
from django.conf import settings

from .models import Event, EventRegistration, Comment, UserProfile, EventCreationLog


# ══════════════════════════════════════════════
# HELPER: obtener rol del usuario
# ══════════════════════════════════════════════


def get_rol(user):
    """Devuelve el rol del usuario o 'fighter' por defecto."""
    perfil = getattr(user, "profile", None)
    return perfil.rol if perfil else "fighter"


# ══════════════════════════════════════════════
# VISTAS DE PAGINA
# ══════════════════════════════════════════════


@csrf_exempt
def login_view(request):
    """Login: redirige a /promotor/ o /peleador/ segun el rol."""
    if request.user.is_authenticated:
        return _redirect_by_rol(request.user)

    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            rol = get_rol(user)
            return JsonResponse({"ok": True, "rol": rol})
        return JsonResponse(
            {"ok": False, "error": "Credenciales incorrectas"}, status=400
        )

    return render(request, "events/login.html")


@csrf_exempt
def register_view(request):
    """Registro: redirige segun rol tras crear la cuenta."""
    if request.user.is_authenticated:
        return _redirect_by_rol(request.user)

    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")
        rol = data.get("rol", "fighter")

        if rol not in ("fighter", "promoter"):
            rol = "fighter"

        if User.objects.filter(username=username).exists():
            return JsonResponse(
                {"ok": False, "error": "El usuario ya existe"}, status=400
            )

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        UserProfile.objects.create(user=user, rol=rol)
        login(request, user)
        return JsonResponse({"ok": True, "rol": rol})

    return render(request, "events/register.html")


def logout_view(request):
    logout(request)
    return redirect("login")


def _redirect_by_rol(user):
    """Redirige al dashboard correspondiente segun el rol."""
    rol = get_rol(user)
    if rol == "promoter":
        return redirect("dashboard_promotor")
    return redirect("dashboard_peleador")


@login_required
def index(request):
    """Redirige al dashboard correcto segun rol."""
    return _redirect_by_rol(request.user)


@login_required
def dashboard_promotor(request):
    """Dashboard exclusivo para promotores."""
    if get_rol(request.user) != "promoter":
        return redirect("dashboard_peleador")
    return render(request, "events/index_promotor.html")


@login_required
def dashboard_peleador(request):
    """Dashboard exclusivo para peleadores."""
    if get_rol(request.user) != "fighter":
        return redirect("dashboard_promotor")
    return render(request, "events/index_peleador.html")


@login_required
def perfil_view(request):
    """Pagina de edicion de perfil (solo peleadores)."""
    if get_rol(request.user) != "fighter":
        return redirect("dashboard_promotor")
    return render(request, "events/perfil.html")


@login_required
def event_detail(request, pk):
    """Detalle de un evento: asistentes y comentarios."""
    return render(request, "events/event_detail.html", {"event_id": pk})


@login_required
def my_qr(request, registration_id):
    """Muestra el QR del usuario para un evento."""
    reg = get_object_or_404(EventRegistration, pk=registration_id, usuario=request.user)
    return render(request, "events/my_qr.html", {"registration": reg})


# ══════════════════════════════════════════════
# API JSON - Eventos
# ══════════════════════════════════════════════


@login_required
def api_events(request):
    if request.method == "GET":
        events = Event.objects.filter(estado="activo").select_related("creador")
        data = [
            {
                "id": e.id,
                "titulo": e.titulo,
                "descripcion": e.descripcion,
                "fecha": e.fecha.strftime("%d/%m/%Y %H:%M"),
                "ubicacion": e.ubicacion,
                "estado": e.estado,
                "creador": e.creador.username,
            }
            for e in events
        ]
        return JsonResponse({"events": data})

    if request.method == "POST":
        if get_rol(request.user) != "promoter":
            return JsonResponse(
                {"error": "Solo los promotores pueden crear eventos"}, status=403
            )

        data = json.loads(request.body)
        event = Event.objects.create(
            titulo=data["titulo"],
            descripcion=data["descripcion"],
            fecha=data["fecha"],
            ubicacion=data["ubicacion"],
            creador=request.user,
        )
        EventCreationLog.objects.create(
            evento=event, creador=request.user, estatus="aprobado"
        )
        return JsonResponse({"ok": True, "id": event.id}, status=201)

    return JsonResponse({"error": "Metodo no permitido"}, status=405)


@login_required
def api_mis_eventos(request):
    if get_rol(request.user) != "promoter":
        return JsonResponse({"error": "Sin permiso"}, status=403)

    events = Event.objects.filter(creador=request.user).order_by("-fecha_creacion")
    data = [
        {
            "id": e.id,
            "titulo": e.titulo,
            "descripcion": e.descripcion,
            "fecha": e.fecha.strftime("%d/%m/%Y %H:%M"),
            "ubicacion": e.ubicacion,
            "estado": e.estado,
            "total_registros": e.registros.count(),
        }
        for e in events
    ]
    return JsonResponse({"events": data})


@login_required
def api_event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "GET":
        return JsonResponse(
            {
                "id": event.id,
                "titulo": event.titulo,
                "descripcion": event.descripcion,
                "fecha": event.fecha.strftime("%d/%m/%Y %H:%M"),
                "ubicacion": event.ubicacion,
                "estado": event.estado,
                "creador": event.creador.username,
            }
        )

    if request.method == "DELETE":
        if event.creador != request.user and not request.user.is_staff:
            return JsonResponse({"error": "Sin permiso"}, status=403)
        event.delete()
        return JsonResponse({"ok": True})

    return JsonResponse({"error": "Metodo no permitido"}, status=405)


# ══════════════════════════════════════════════
# API JSON - Registro a eventos
# ══════════════════════════════════════════════


def _generar_qr(codigo, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(codigo)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_dir = os.path.join(settings.MEDIA_ROOT, "qrcodes")
    os.makedirs(qr_dir, exist_ok=True)

    ruta = os.path.join(qr_dir, filename)
    img.save(ruta)
    return f"qrcodes/{filename}"


@login_required
def api_register_event(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    if get_rol(request.user) == "promoter":
        return JsonResponse(
            {"error": "Los promotores no pueden registrarse como asistentes"},
            status=403,
        )

    data = json.loads(request.body)
    event = get_object_or_404(Event, pk=data["evento_id"])

    if EventRegistration.objects.filter(usuario=request.user, evento=event).exists():
        return JsonResponse(
            {"ok": False, "error": "Ya estas registrado en este evento"}, status=400
        )

    codigo = str(uuid.uuid4())
    filename = f"{codigo}.png"
    ruta_imagen = _generar_qr(codigo, filename)

    reg = EventRegistration.objects.create(
        usuario=request.user,
        evento=event,
        codigo_qr=codigo,
        imagen_qr=ruta_imagen,
    )
    return JsonResponse(
        {"ok": True, "registration_id": reg.id, "codigo_qr": codigo}, status=201
    )


@login_required
def api_attendees(request, pk):
    event = get_object_or_404(Event, pk=pk)
    registros = EventRegistration.objects.filter(evento=event).select_related(
        "usuario__profile"
    )
    data = [
        {
            "usuario": r.usuario.username,
            "foto": r.usuario.profile.foto.url
            if hasattr(r.usuario, "profile") and r.usuario.profile.foto
            else None,
            "estado": r.estado,
            "check_in": r.check_in,
        }
        for r in registros
    ]
    return JsonResponse({"attendees": data, "total": len(data)})


@login_required
def api_my_registration(request, pk):
    try:
        reg = EventRegistration.objects.get(usuario=request.user, evento_id=pk)
        return JsonResponse(
            {"registered": True, "registration_id": reg.id, "codigo_qr": reg.codigo_qr}
        )
    except EventRegistration.DoesNotExist:
        return JsonResponse({"registered": False})


# ══════════════════════════════════════════════
# API JSON - Comentarios
# ══════════════════════════════════════════════


@login_required
def api_comments(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == "GET":
        comments = Comment.objects.filter(evento=event).select_related("usuario")
        data = [
            {
                "usuario": c.usuario.username,
                "contenido": c.contenido,
                "fecha": c.fecha_comentario.strftime("%d/%m/%Y %H:%M"),
            }
            for c in comments
        ]
        return JsonResponse({"comments": data})

    if request.method == "POST":
        data = json.loads(request.body)
        Comment.objects.create(
            evento=event,
            usuario=request.user,
            contenido=data["contenido"],
        )
        return JsonResponse({"ok": True}, status=201)

    return JsonResponse({"error": "Metodo no permitido"}, status=405)


# ══════════════════════════════════════════════
# API JSON - Check-in por QR
# ══════════════════════════════════════════════


@login_required
def api_checkin(request):
    if request.method != "POST":
        return JsonResponse({"error": "Metodo no permitido"}, status=405)

    data = json.loads(request.body)
    codigo = data.get("codigo_qr", "")

    try:
        reg = EventRegistration.objects.select_related("evento", "usuario").get(
            codigo_qr=codigo
        )
    except EventRegistration.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Codigo QR invalido"}, status=404)

    if reg.evento.creador != request.user and not request.user.is_staff:
        return JsonResponse(
            {"ok": False, "error": "Solo el promotor del evento puede hacer check-in"},
            status=403,
        )

    if reg.check_in:
        return JsonResponse(
            {"ok": False, "error": "Ya se realizo el check-in"}, status=400
        )

    reg.check_in = True
    reg.estado = "confirmado"
    reg.save()

    return JsonResponse(
        {
            "ok": True,
            "usuario": reg.usuario.username,
            "evento": reg.evento.titulo,
        }
    )


# ══════════════════════════════════════════════
# API - Info y edicion del usuario actual
# ══════════════════════════════════════════════


@login_required
def api_me(request):
    perfil = getattr(request.user, "profile", None)

    if request.method == "GET":
        return JsonResponse(
            {
                "username": request.user.username,
                "email": request.user.email,
                "rol": perfil.rol if perfil else "fighter",
                "bio": perfil.bio if perfil else "",
                "foto": perfil.foto.url if perfil and perfil.foto else None,
                "peso": str(perfil.peso) if perfil and perfil.peso else None,
                "disciplina": perfil.disciplina if perfil else None,
                "edad": perfil.edad if perfil else None,
            }
        )

    if request.method == "POST":
        if get_rol(request.user) != "fighter":
            return JsonResponse(
                {"error": "Solo los peleadores pueden editar su perfil"}, status=403
            )

        data = json.loads(request.body)
        email = data.get("email", "").strip()
        bio = data.get("bio", "").strip()
        peso = data.get("peso")
        disciplina = data.get("disciplina", "").strip()
        edad = data.get("edad")

        if email:
            request.user.email = email
            request.user.save()

        if perfil:
            perfil.bio = bio
            if peso:
                perfil.peso = peso
            if disciplina:
                perfil.disciplina = disciplina
            if edad:
                perfil.edad = edad
            perfil.save()

        return JsonResponse({"ok": True})

    return JsonResponse({"error": "Metodo no permitido"}, status=405)


@login_required
def api_me_upload_foto(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    if get_rol(request.user) != "fighter":
        return JsonResponse(
            {"error": "Solo los peleadores pueden editar su perfil"}, status=403
        )

    perfil = getattr(request.user, "profile", None)
    if not perfil:
        return JsonResponse({"error": "Perfil no encontrado"}, status=404)

    foto = request.FILES.get("foto")
    if not foto:
        return JsonResponse({"error": "No se recibió ninguna imagen"}, status=400)

    if foto.size > 5 * 1024 * 1024:
        return JsonResponse({"error": "La imagen no puede exceder 5MB"}, status=400)

    perfil.foto = foto
    perfil.save()

    return JsonResponse({"ok": True, "foto": perfil.foto.url})
