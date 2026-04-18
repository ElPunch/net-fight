"""
views.py - Vistas de paginas (templates) de Fight.net
Todas las respuestas JSON viven en events/api_views.py (DRF).
"""

import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from .models import EventRegistration, UserProfile


def get_rol(user):
    perfil = getattr(user, 'profile', None)
    return perfil.rol if perfil else 'fighter'


def _redirect_by_rol(user):
    rol = get_rol(user)
    if rol == 'promoter':
        return redirect('dashboard_promotor')
    return redirect('dashboard_peleador')


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
