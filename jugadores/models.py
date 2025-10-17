from typing import TYPE_CHECKING, Any
from django.utils.translation import gettext_lazy as _
from datetime import date

# Modelo para torneos

# jugadores/models.py
if TYPE_CHECKING:
    # Imports only for type checkers / editors when Django is available
    from django.db import models  # pragma: no cover
    from django.contrib.auth.models import User  # pragma: no cover
    from django.apps import apps  # pragma: no cover
else:
    try:
        # Runtime imports when Django is installed
        from django.db import models
        from django.contrib.auth.models import User
        from django.apps import apps
    except Exception:
        # Fallback objects so linters/editors won't report unresolved imports
        class _models:
            class Model:  # minimal stand-in for models.Model
                pass

            @staticmethod
            def CharField(*args, **kwargs):
                return None

            @staticmethod
            def ImageField(*args, **kwargs):
                return None

            @staticmethod
            def ManyToManyField(*args, **kwargs):
                return None

            @staticmethod
            def OneToOneField(*args, **kwargs):
                return None

            @staticmethod
            def ForeignKey(*args, **kwargs):
                return None

            @staticmethod
            def DateField(*args, **kwargs):
                return None

            @staticmethod
            def IntegerField(*args, **kwargs):
                return None

            @staticmethod
            def DateTimeField(*args, **kwargs):
                return None

        models = _models
        User = Any

        class apps:
            @staticmethod
            def get_model(app_label, model_name):
                # Minimal dummy model with objects.get_or_create used by get_default_equipo_id
                class DummyEquipo:
                    id = 1
                    nombre = "Furia Nocturna FC"
                    objects = type("o", (), {"get_or_create": lambda *args, **kwargs: (DummyEquipo(), False)})
                return DummyEquipo

# --- Nuevo: Función para obtener o crear la ID del equipo predeterminado ---
def get_default_equipo_id():
    """
    Retorna la ID del equipo 'Furia Nocturna FC'.
    Si no existe, lo crea. Si ya existe, no lo recrea.
    """
    # Usar apps.get_model para evitar dependencias circulares en import time
    Equipo = apps.get_model('jugadores', 'Equipo')
    equipo, creado = Equipo.objects.get_or_create(nombre=_("Furia Nocturna FC"))
    return equipo.id

# Modelo para los datos del equipo
class Equipo(models.Model):
    """
    Modelo para los datos del equipo de fútbol.
    """
    nombre = models.CharField(_('nombre'), max_length=100, unique=True)
    # logo = models.ImageField(_('logo'), upload_to='equipos/logos/', blank=True, null=True)
    torneos = models.ManyToManyField('Torneo', related_name='equipos', blank=True, verbose_name=_('torneos'))
    imagen_url = models.URLField(
        max_length=500,  # Suficiente longitud para la URL de Imgur
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.nombre

# Modelo para los datos del jugador
class Jugador(models.Model):
    """
    Modelo para los datos del jugador.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('usuario'))
    nombre = models.CharField(_('nombre'), max_length=100)
    apellido = models.CharField(_('apellido'), max_length=100)
    # La cédula debe ser obligatoria y única.
    cedula = models.CharField(_('cédula'), max_length=8, unique=True)
    fecha_de_nacimiento = models.DateField(_('fecha de nacimiento'), null=True, blank=True)
    # Edad calculada a partir de fecha_de_nacimiento. Se guarda en la BD para consultas rápidas.
    edad = models.PositiveSmallIntegerField(_('edad'), null=True, blank=True, editable=False)
    posicion = models.CharField(_('posición'), max_length=50)
    numero_de_camiseta = models.IntegerField(_('número de camiseta'), null=True, blank=True)
    # foto_de_perfil = models.ImageField(_('foto de perfil'), upload_to='fotos_perfil/', null=True, blank=True)
    imagen_url = models.URLField(
        max_length=500,  # Suficiente longitud para la URL de Imgur
        null=True, 
        blank=True
    )
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, default=get_default_equipo_id, verbose_name=_('equipo'))

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def calcular_edad(self):
        """
        Calcula la edad en años a partir de `fecha_de_nacimiento`.
        Retorna None si no hay fecha de nacimiento.
        """
        if not self.fecha_de_nacimiento:
            return None
        today = date.today()
        dob = self.fecha_de_nacimiento
        # Resta 1 si el cumpleaños de este año aún no ocurrió
        edad = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return edad

    def save(self, *args, **kwargs):
        # Antes de guardar, actualizar el campo edad basado en fecha_de_nacimiento
        try:
            self.edad = self.calcular_edad()
        except Exception:
            # En caso de cualquier problema de cálculo, no impedir el guardado
            self.edad = None
        super().save(*args, **kwargs)

# Modelo para los partidos
class Partido(models.Model):
    """
    Modelo para los partidos jugados entre equipos.
    """
    torneo = models.ForeignKey('Torneo', on_delete=models.CASCADE, related_name='partidos', null=True, blank=True, verbose_name=_('torneo'))
    equipo_local = models.ForeignKey(Equipo, related_name='partidos_local', on_delete=models.CASCADE, verbose_name=_('equipo local'))
    equipo_visitante = models.ForeignKey(Equipo, related_name='partidos_visitante', on_delete=models.CASCADE, verbose_name=_('equipo visitante'))
    fecha = models.DateField(_('fecha'))
    marcador_local = models.IntegerField(_('marcador local'), null=True, blank=True)
    marcador_visitante = models.IntegerField(_('marcador visitante'), null=True, blank=True)
    jugador_partido = models.ForeignKey('Jugador', on_delete=models.SET_NULL, null=True, blank=True, related_name='partidos_destacado', verbose_name=_('jugador destacado'))
    estado = models.CharField(_('estado'), max_length=20, choices=[('proximo', _('Próximo')), ('jugado', _('Jugado'))], default='proximo')

    def es_proximo(self):
        return self.estado == 'proximo'

    def es_jugado(self):
        return self.estado == 'jugado'

    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante} - {self.fecha}"

# Modelo para votaciones de Jugador del Partido
class VotacionJugadorPartido(models.Model):
    """
    Modelo para votaciones de Jugador del Partido.
    """
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='votaciones', verbose_name=_('partido'))
    jugador = models.ForeignKey('Jugador', on_delete=models.CASCADE, verbose_name=_('jugador'))
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('usuario'))
    fecha = models.DateTimeField(_('fecha'), auto_now_add=True)
    def __str__(self):
        return f'Voto de {self.usuario} para {self.jugador} en {self.partido}'

# Modelo para las estadísticas de un jugador en un partido
class Estadistica(models.Model):
    """
    Modelo para las estadísticas de un partido, incluyendo jugadores que anotaron, asistieron, fueron amonestados y expulsados.
    """
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, verbose_name=_('partido'))
    goles = models.IntegerField(_('goles'), default=0)
    asistencias = models.IntegerField(_('asistencias'), default=0)
    tarjetas_amarillas = models.IntegerField(_('tarjetas amarillas'), default=0)
    tarjetas_rojas = models.IntegerField(_('tarjetas rojas'), default=0)
    anotadores = models.ManyToManyField('Jugador', related_name='goles_partidos', blank=True, verbose_name=_('anotadores'))
    asistentes = models.ManyToManyField('Jugador', related_name='asistencias_partidos', blank=True, verbose_name=_('asistentes'))
    amonestados = models.ManyToManyField('Jugador', related_name='amonestados_partidos', blank=True, verbose_name=_('amonestados'))
    expulsados = models.ManyToManyField('Jugador', related_name='expulsados_partidos', blank=True, verbose_name=_('expulsados'))


    def __str__(self):
        return f"Estadísticas del partido {self.partido}"


class Tarjeta(models.Model):
    """
    Modelo para registrar tarjetas por jugador en un partido.
    Permite múltiples amarillas (hasta 2) y como máximo 1 roja por jugador/partido.
    Cuando se registra la segunda amarilla se crea automáticamente la roja si no existe.
    """
    TIPO_CHOICES = [
        ('amarilla', _('Amarilla')),
        ('roja', _('Roja')),
    ]

    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='tarjetas', verbose_name=_('partido'))
    jugador = models.ForeignKey('Jugador', on_delete=models.CASCADE, related_name='tarjetas', verbose_name=_('jugador'))
    tipo = models.CharField(_('tipo'), max_length=10, choices=TIPO_CHOICES)
    minuto = models.IntegerField(_('minuto'), null=True, blank=True)
    fecha = models.DateTimeField(_('fecha'), auto_now_add=True)
    anulada = models.BooleanField(_('anulada'), default=False)
    motivo_anulacion = models.TextField(_('motivo anulación'), null=True, blank=True)

    class Meta:
        verbose_name = _('Tarjeta')
        verbose_name_plural = _('Tarjetas')

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.jugador} en {self.partido}"

    def clean(self):
        # Validaciones antes de guardar
        from django.core.exceptions import ValidationError
        # comprobar rojas existentes
        if self.tipo == 'roja':
            qs = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='roja', anulada=False)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(_('Ya existe una tarjeta roja para este jugador en este partido.'))

        if self.tipo == 'amarilla':
            qs = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='amarilla', anulada=False)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.count() >= 2:
                raise ValidationError(_('No se pueden asignar más de 2 tarjetas amarillas a un jugador en un partido.'))

    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        # Ejecutar clean para validar condiciones
        self.clean()
        # Guardamos la tarjeta actual
        created_new = self.pk is None
        super().save(*args, **kwargs)

        # Si acabamos de guardar una segunda amarilla, creamos la roja automáticamente
        if self.tipo == 'amarilla':
            amarillas_qs = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='amarilla', anulada=False).order_by('fecha')
            amarillas = amarillas_qs.count()
            has_roja = Tarjeta.objects.filter(partido=self.partido, jugador=self.jugador, tipo='roja', anulada=False).exists()
            if amarillas >= 2 and not has_roja:
                # Intentar usar el minuto de la segunda amarilla; si no está disponible, usar minuto de la actual
                segunda = amarillas_qs[1] if amarillas_qs.count() > 1 else None
                minuto_roja = None
                if segunda and getattr(segunda, 'minuto', None):
                    minuto_roja = segunda.minuto
                elif getattr(self, 'minuto', None):
                    minuto_roja = self.minuto
                # crear roja automática con minuto si lo tenemos
                Tarjeta.objects.create(partido=self.partido, jugador=self.jugador, tipo='roja', minuto=minuto_roja, anulada=False)


# Modelo para las fotos de la galería

# Modelo para los comentarios de los jugadores
    
class Torneo(models.Model):
    """
    Modelo para los torneos en los que participa el club.
    """
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.nombre


class Pago(models.Model):
    """
    Modelo para registrar pagos de jugadores: inscripción, arbitraje y tarjetas.
    """
    TIPO_PAGO_CHOICES = [
        ('inscripcion', _('Inscripción')),
        ('arbitraje', _('Arbitraje')),
        ('tarjetas_amarilla', _('Tarjeta Amarilla')),
        ('tarjetas_roja', _('Tarjeta Roja')),
        ('otro', _('Otro')),
    ]

    METODO_PAGO_CHOICES = [
        ('transferencia', _('Transferencia')),
        ('pago_movil', _('Pago Móvil')),
        ('efectivo', _('Efectivo/Divisas')),
        ('otro', _('Otro')),
    ]

    ESTADO_CHOICES = [
        ('pendiente', _('Pendiente')),
        ('aprobado', _('Aprobado')),
        ('rechazado', _('Rechazado')),
    ]

    jugador = models.ForeignKey('Jugador', on_delete=models.CASCADE, related_name='pagos', verbose_name=_('jugador'))
    tipo = models.CharField(_('tipo de pago'), max_length=20, choices=TIPO_PAGO_CHOICES)
    monto = models.DecimalField(_('monto'), max_digits=8, decimal_places=2)
    metodo = models.CharField(_('método de pago'), max_length=50, choices=METODO_PAGO_CHOICES)
    referencia = models.CharField(_('referencia'), max_length=6, null=True, blank=True)
    comprobante = models.ImageField(_('comprobante'), upload_to='pagos/comprobantes/', null=True, blank=True)
    descripcion = models.TextField(_('descripción'), max_length=50, null=True, blank=True)
    MONEDA_CHOICES = [
        ('VES', _('Bolívares (Bs)')),
        ('USD', _('Dólares (USD)')),
    ]
    moneda = models.CharField(_('moneda'), max_length=3, choices=MONEDA_CHOICES, default='VES')
    fecha = models.DateTimeField(_('fecha'), auto_now_add=True)
    estado = models.CharField(_('estado'), max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    motivo_rechazo = models.TextField(_('motivo rechazo'), null=True, blank=True)
    archivado = models.BooleanField(_('archivado'), default=False)

    class Meta:
        verbose_name = _('Pago')
        verbose_name_plural = _('Pagos')

    def __str__(self):
        return f"{self.jugador} - {self.get_tipo_display()} - {self.monto} ({self.estado})"
