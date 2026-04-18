"""
models.py - Modelos de Fight.net
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

    DISCIPLINA_CHOICES = [
        ('mma',        'MMA'),
        ('boxeo',      'Boxeo'),
        ('kickboxing', 'Kickboxing'),
        ('jiujitsu',   'Jiu-Jitsu'),
        ('muaythai',   'Muay Thai'),
        ('lucha',      'Lucha Libre'),
        ('karate',     'Karate'),
        ('otro',       'Otro'),
    ]

    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rol         = models.CharField(max_length=10, choices=ROL_CHOICES, default='fighter')
    bio         = models.TextField(blank=True, null=True)

    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    disciplina  = models.CharField(max_length=20, choices=DISCIPLINA_CHOICES, blank=True, null=True)
    categoria   = models.CharField(max_length=50, blank=True, null=True)
    peso_kg     = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    estatura_cm = models.IntegerField(blank=True, null=True)
    edad        = models.IntegerField(blank=True, null=True)

    victorias   = models.IntegerField(default=0)
    derrotas    = models.IntegerField(default=0)
    empates     = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuarios'

    def __str__(self):
        return f'{self.user.username} ({self.get_rol_display()})'

    @property
    def foto_url(self):
        if self.foto_perfil:
            return self.foto_perfil.url
        return None


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
        return f'{self.titulo} - {self.fecha.strftime("%d/%m/%Y")}'


# ──────────────────────────────────────────────
# TABLA 3: Registro a evento
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
    codigo_qr      = models.CharField(max_length=100, unique=True, blank=True)
    imagen_qr      = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    check_in       = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Registro a evento'
        verbose_name_plural = 'Registros a eventos'
        unique_together = ('usuario', 'evento')

    def __str__(self):
        return f'{self.usuario.username} -> {self.evento.titulo}'


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
# TABLA 5: Enfrentamientos (cartelera)
# ──────────────────────────────────────────────
class Fight(models.Model):
    """Enfrentamiento entre dos peleadores dentro de un evento."""
    evento     = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='enfrentamientos',
    )
    peleador_a = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='peleas_como_a',
    )
    peleador_b = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='peleas_como_b',
    )
    orden      = models.PositiveIntegerField(default=1)
    titulo     = models.CharField(
        max_length=200, blank=True,
        help_text='Nombre opcional de la pelea (ej: Pelea estelar)',
    )
    notas      = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Enfrentamiento'
        verbose_name_plural = 'Enfrentamientos'
        ordering = ['evento', 'orden']
        constraints = [
            models.CheckConstraint(
                check=~models.Q(peleador_a=models.F('peleador_b')),
                name='fight_distinct_fighters',
            ),
        ]

    def __str__(self):
        return f'{self.peleador_a.username} vs {self.peleador_b.username} ({self.evento.titulo})'


# ──────────────────────────────────────────────
# TABLA 6: Auditoria de creacion de eventos
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

    class Meta:
        verbose_name = 'Log de creacion de evento'
        verbose_name_plural = 'Logs de creacion de eventos'

    def __str__(self):
        return f'Log: {self.evento.titulo} - {self.get_estatus_display()}'
