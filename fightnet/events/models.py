"""
models.py – Modelos de Fight.net
5 tablas principales con relaciones claras.

Decisión de diseño: usamos el modelo User de Django (auth.User) en lugar de
crear uno propio. Esto evita duplicar lógica de autenticación y cumple con
"sin sobreingeniería". Añadimos un perfil (UserProfile) para el campo 'rol'.
"""

from django.db import models
from django.contrib.auth.models import User


# ──────────────────────────────────────────────
# TABLA 1: Perfil de usuario (extiende auth.User)
# ──────────────────────────────────────────────
class UserProfile(models.Model):
    ROL_CHOICES = [
        ('fighter',  'Peleador'),
        ('promoter', 'Promotor'),
        ('admin',    'Administrador'),
    ]

    user     = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rol      = models.CharField(max_length=10, choices=ROL_CHOICES, default='fighter')
    bio      = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuarios'

    def __str__(self):
        return f'{self.user.username} ({self.get_rol_display()})'


# ──────────────────────────────────────────────
# TABLA 2: Evento
# ──────────────────────────────────────────────
class Event(models.Model):
    ESTADO_CHOICES = [
        ('activo',     'Activo'),
        ('cancelado',  'Cancelado'),
        ('finalizado', 'Finalizado'),
    ]

    titulo        = models.CharField(max_length=200)
    descripcion   = models.TextField()
    fecha         = models.DateTimeField()
    ubicacion     = models.CharField(max_length=300)
    estado        = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activo')
    creador       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='eventos_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.titulo} – {self.fecha.strftime("%d/%m/%Y")}'


# ──────────────────────────────────────────────
# TABLA 3: Registro a evento (tabla intermedia Users ↔ Events)
# Aquí también se almacena el QR de cada inscripción.
# Decisión: incluir el QR aquí (campo imagen) en lugar de tabla separada,
# ya que el profesor pide "básico". La tabla EventCheckIn del PDF
# se omite para no sobrecomplicar.
# ──────────────────────────────────────────────
class EventRegistration(models.Model):
    ESTADO_CHOICES = [
        ('registrado',  'Registrado'),
        ('confirmado',  'Confirmado'),
        ('cancelado',   'Cancelado'),
    ]

    usuario        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros')
    evento         = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registros')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado         = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='registrado')
    codigo_qr      = models.CharField(max_length=100, unique=True, blank=True)  # código único
    imagen_qr      = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    check_in       = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Registro a evento'
        verbose_name_plural = 'Registros a eventos'
        unique_together = ('usuario', 'evento')   # un usuario no se registra dos veces

    def __str__(self):
        return f'{self.usuario.username} → {self.evento.titulo}'


# ──────────────────────────────────────────────
# TABLA 4: Comentarios
# ──────────────────────────────────────────────
class Comment(models.Model):
    evento          = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='comentarios')
    usuario         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios')
    contenido       = models.TextField()
    fecha_comentario = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['-fecha_comentario']

    def __str__(self):
        return f'{self.usuario.username} en "{self.evento.titulo}"'


# ──────────────────────────────────────────────
# TABLA 5: Auditoría de creación de eventos
# Cubre el requisito del PDF (EventCreation) y sirve como 5.ª tabla.
# ──────────────────────────────────────────────
class EventCreationLog(models.Model):
    ESTATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado',  'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    evento          = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='log_creacion')
    creador         = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion  = models.DateTimeField(auto_now_add=True)
    estatus         = models.CharField(max_length=15, choices=ESTATUS_CHOICES, default='aprobado')
    # Nota: en este proyecto académico los eventos se aprueban automáticamente.
    # El admin puede cambiar el estatus desde el panel si lo desea.

    class Meta:
        verbose_name = 'Log de creación de evento'
        verbose_name_plural = 'Logs de creación de eventos'

    def __str__(self):
        return f'Log: {self.evento.titulo} – {self.get_estatus_display()}'

