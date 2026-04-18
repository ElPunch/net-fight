"""
serializers.py - Serializadores de Django Rest Framework para Fight.net
"""

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    UserProfile,
    Event,
    EventRegistration,
    Comment,
    Fight,
    EventCreationLog,
)


# ══════════════════════════════════════════════
# Usuario / Perfil
# ══════════════════════════════════════════════

class FighterBriefSerializer(serializers.ModelSerializer):
    """Resumen ligero de un peleador, para anidarlo en peleas/asistentes."""
    username    = serializers.CharField(source='user.username', read_only=True)
    user_id     = serializers.IntegerField(source='user.id',    read_only=True)
    foto_perfil = serializers.SerializerMethodField()
    disciplina  = serializers.SerializerMethodField()

    class Meta:
        model  = UserProfile
        fields = ('user_id', 'username', 'foto_perfil', 'disciplina', 'categoria',
                  'peso_kg', 'victorias', 'derrotas', 'empates')

    def get_foto_perfil(self, obj):
        return obj.foto_url

    def get_disciplina(self, obj):
        return obj.get_disciplina_display() if obj.disciplina else None


class UserSerializer(serializers.ModelSerializer):
    rol         = serializers.CharField(source='profile.rol', read_only=True)
    foto_perfil = serializers.SerializerMethodField()
    disciplina  = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ('id', 'username', 'email', 'rol', 'foto_perfil', 'disciplina')

    def get_foto_perfil(self, obj):
        perfil = getattr(obj, 'profile', None)
        return perfil.foto_url if perfil else None

    def get_disciplina(self, obj):
        perfil = getattr(obj, 'profile', None)
        if perfil and perfil.disciplina:
            return perfil.get_disciplina_display()
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    username     = serializers.CharField(source='user.username', read_only=True)
    email        = serializers.EmailField(source='user.email')
    disciplina_display = serializers.CharField(source='get_disciplina_display', read_only=True)
    foto_perfil  = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = UserProfile
        fields = (
            'username', 'email', 'rol', 'bio',
            'foto_perfil', 'disciplina', 'disciplina_display', 'categoria',
            'peso_kg', 'estatura_cm', 'edad',
            'victorias', 'derrotas', 'empates',
        )
        read_only_fields = ('rol',)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data and 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save(update_fields=['email'])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ══════════════════════════════════════════════
# Enfrentamientos (Fight)
# ══════════════════════════════════════════════

class FightSerializer(serializers.ModelSerializer):
    """Serializador usado al leer y mostrar un enfrentamiento."""
    peleador_a_info = serializers.SerializerMethodField(read_only=True)
    peleador_b_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Fight
        fields = (
            'id',
            'evento',
            'peleador_a', 'peleador_b',
            'peleador_a_info', 'peleador_b_info',
            'orden', 'titulo', 'notas',
        )
        read_only_fields = ('evento',)

    def _user_info(self, user):
        perfil = getattr(user, 'profile', None)
        return {
            'id':          user.id,
            'username':    user.username,
            'foto_perfil': perfil.foto_url if perfil else None,
            'disciplina':  perfil.get_disciplina_display() if perfil and perfil.disciplina else None,
            'categoria':   perfil.categoria if perfil else None,
            'record':      f'{perfil.victorias}-{perfil.derrotas}-{perfil.empates}' if perfil else '0-0-0',
        }

    def get_peleador_a_info(self, obj):
        return self._user_info(obj.peleador_a)

    def get_peleador_b_info(self, obj):
        return self._user_info(obj.peleador_b)

    def validate(self, attrs):
        a = attrs.get('peleador_a')
        b = attrs.get('peleador_b')
        if a and b and a.id == b.id:
            raise serializers.ValidationError(
                'Un enfrentamiento debe tener dos peleadores distintos.'
            )
        for peleador in (a, b):
            if peleador is None:
                continue
            perfil = getattr(peleador, 'profile', None)
            if not perfil or perfil.rol != 'fighter':
                raise serializers.ValidationError(
                    f'El usuario {peleador.username} no tiene rol de peleador.'
                )
        return attrs


class FightWriteNestedSerializer(serializers.Serializer):
    """
    Serializador usado solamente al crear enfrentamientos anidados junto con
    el evento (entrada POST en /api/events/).
    """
    peleador_a = serializers.IntegerField()
    peleador_b = serializers.IntegerField()
    orden      = serializers.IntegerField(required=False, default=1)
    titulo     = serializers.CharField(required=False, allow_blank=True, default='')
    notas      = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['peleador_a'] == attrs['peleador_b']:
            raise serializers.ValidationError(
                'Un enfrentamiento debe tener dos peleadores distintos.'
            )
        ids = [attrs['peleador_a'], attrs['peleador_b']]
        peleadores = {
            u.id: u for u in User.objects
            .select_related('profile')
            .filter(id__in=ids)
        }
        for uid in ids:
            u = peleadores.get(uid)
            if not u:
                raise serializers.ValidationError(
                    f'No existe un usuario con id {uid}.'
                )
            perfil = getattr(u, 'profile', None)
            if not perfil or perfil.rol != 'fighter':
                raise serializers.ValidationError(
                    f'El usuario {u.username} no tiene rol de peleador.'
                )
        return attrs


# ══════════════════════════════════════════════
# Eventos
# ══════════════════════════════════════════════

class EventSerializer(serializers.ModelSerializer):
    creador          = serializers.CharField(source='creador.username', read_only=True)
    total_registros  = serializers.SerializerMethodField(read_only=True)
    enfrentamientos  = FightSerializer(many=True, read_only=True)
    fecha_formateada = serializers.SerializerMethodField(read_only=True)

    # Campo write-only para crear enfrentamientos junto con el evento
    enfrentamientos_input = FightWriteNestedSerializer(
        many=True, write_only=True, required=False,
    )

    class Meta:
        model  = Event
        fields = (
            'id', 'titulo', 'descripcion', 'fecha', 'fecha_formateada',
            'ubicacion', 'estado', 'creador',
            'fecha_creacion', 'total_registros',
            'enfrentamientos', 'enfrentamientos_input',
        )
        read_only_fields = ('estado', 'fecha_creacion')

    def get_total_registros(self, obj):
        return obj.registros.count()

    def get_fecha_formateada(self, obj):
        return obj.fecha.strftime('%d/%m/%Y %H:%M')

    def create(self, validated_data):
        enfrentamientos = validated_data.pop('enfrentamientos_input', [])
        user = self.context['request'].user
        event = Event.objects.create(creador=user, **validated_data)
        for idx, pelea in enumerate(enfrentamientos, start=1):
            Fight.objects.create(
                evento     = event,
                peleador_a_id = pelea['peleador_a'],
                peleador_b_id = pelea['peleador_b'],
                orden      = pelea.get('orden') or idx,
                titulo     = pelea.get('titulo', ''),
                notas      = pelea.get('notas', ''),
            )
        EventCreationLog.objects.create(evento=event, creador=user, estatus='aprobado')
        return event


# ══════════════════════════════════════════════
# Registros a evento
# ══════════════════════════════════════════════

class EventRegistrationSerializer(serializers.ModelSerializer):
    usuario      = serializers.CharField(source='usuario.username', read_only=True)
    foto_perfil  = serializers.SerializerMethodField(read_only=True)
    disciplina   = serializers.SerializerMethodField(read_only=True)
    categoria    = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = EventRegistration
        fields = (
            'id', 'usuario', 'evento', 'estado', 'check_in',
            'codigo_qr', 'foto_perfil', 'disciplina', 'categoria',
            'fecha_registro',
        )
        read_only_fields = ('codigo_qr', 'fecha_registro', 'estado', 'check_in')

    def get_foto_perfil(self, obj):
        perfil = getattr(obj.usuario, 'profile', None)
        return perfil.foto_url if perfil else None

    def get_disciplina(self, obj):
        perfil = getattr(obj.usuario, 'profile', None)
        if perfil and perfil.disciplina:
            return perfil.get_disciplina_display()
        return None

    def get_categoria(self, obj):
        perfil = getattr(obj.usuario, 'profile', None)
        return perfil.categoria if perfil else None


# ══════════════════════════════════════════════
# Comentarios
# ══════════════════════════════════════════════

class CommentSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source='usuario.username', read_only=True)
    fecha   = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = Comment
        fields = ('id', 'evento', 'usuario', 'contenido', 'fecha_comentario', 'fecha')
        read_only_fields = ('evento', 'fecha_comentario')

    def get_fecha(self, obj):
        return obj.fecha_comentario.strftime('%d/%m/%Y %H:%M')


# ══════════════════════════════════════════════
# Log de auditoria (solo lectura)
# ══════════════════════════════════════════════

class EventCreationLogSerializer(serializers.ModelSerializer):
    creador = serializers.CharField(source='creador.username', read_only=True)
    evento  = serializers.CharField(source='evento.titulo',    read_only=True)

    class Meta:
        model  = EventCreationLog
        fields = ('id', 'evento', 'creador', 'fecha_creacion', 'estatus')
        read_only_fields = fields
