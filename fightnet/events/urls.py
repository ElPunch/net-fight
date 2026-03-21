"""
urls.py – URLs de la app 'events'
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Páginas HTML ──────────────────────────────────
    path('',                        views.index,          name='index'),
    path('login/',                  views.login_view,     name='login'),
    path('register/',               views.register_view,  name='register'),
    path('logout/',                 views.logout_view,    name='logout'),
    path('events/<int:pk>/',        views.event_detail,   name='event_detail'),
    path('my-qr/<int:registration_id>/', views.my_qr,    name='my_qr'),

    # ── API JSON ──────────────────────────────────────
    path('api/events/',                     views.api_events,          name='api_events'),
    path('api/events/<int:pk>/',            views.api_event_detail,    name='api_event_detail'),
    path('api/register-event/',             views.api_register_event,  name='api_register_event'),
    path('api/event-attendees/<int:pk>/',   views.api_attendees,       name='api_attendees'),
    path('api/event-comments/<int:pk>/',    views.api_comments,        name='api_comments'),
    path('api/check-in/',                   views.api_checkin,         name='api_checkin'),
    path('api/me/',                         views.api_me,              name='api_me'),
]
