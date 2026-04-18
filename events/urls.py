"""
urls.py - URLs de la app 'events'
Los endpoints /api/ usan Django Rest Framework.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import api_views


# ══════════════════════════════════════════════
# Router de DRF para ViewSets
# ══════════════════════════════════════════════
router = DefaultRouter()
router.register(r'events', api_views.EventViewSet,            basename='events')
router.register(r'logs',   api_views.EventCreationLogViewSet, basename='logs')


urlpatterns = [
    # ── Autenticacion ─────────────────────────────────
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # ── Dashboards por rol ────────────────────────────
    path('',            views.index,               name='index'),
    path('promotor/',   views.dashboard_promotor,  name='dashboard_promotor'),
    path('peleador/',   views.dashboard_peleador,  name='dashboard_peleador'),
    path('perfil/',     views.perfil_view,         name='perfil'),

    # ── Detalle de evento y QR ────────────────────────
    path('events/<int:pk>/',              views.event_detail, name='event_detail'),
    path('my-qr/<int:registration_id>/',  views.my_qr,        name='my_qr'),

    # ══════════════════════════════════════════════
    # API  - Django Rest Framework
    # ══════════════════════════════════════════════
    # ViewSets registrados en el router -> /api/events/, /api/logs/
    path('api/', include(router.urls)),

    # ── Peleadores disponibles (SOLO GET) ─────────────
    path('api/fighters/',                        api_views.FighterListView.as_view(),   name='api_fighters'),

    # ── Eventos propios del promotor (SOLO GET) ───────
    path('api/mis-eventos/',                     api_views.MisEventosListView.as_view(), name='api_mis_eventos'),

    # ── Registros (POST para peleadores) ──────────────
    path('api/register-event/',                  api_views.RegisterToEventView.as_view(), name='api_register_event'),
    path('api/event-attendees/<int:pk>/',        api_views.EventAttendeesView.as_view(),  name='api_attendees'),
    path('api/my-registration/<int:pk>/',        api_views.MyRegistrationView.as_view(),  name='api_my_registration'),

    # ── Comentarios (GET y POST) ──────────────────────
    path('api/event-comments/<int:pk>/',         api_views.EventCommentsView.as_view(),   name='api_comments'),

    # ── Enfrentamientos (cartelera del evento) ────────
    path('api/events/<int:pk>/fights/',          api_views.EventFightsView.as_view(),     name='api_event_fights'),
    path('api/fights/<int:pk>/',                 api_views.FightDetailView.as_view(),     name='api_fight_detail'),

    # ── Check-in (SOLO POST) ──────────────────────────
    path('api/check-in/',                        api_views.api_checkin,                   name='api_checkin'),

    # ── Perfil del usuario actual ─────────────────────
    path('api/me/',                              api_views.MeView.as_view(),              name='api_me'),
]
