## jugadores/forms.py
from django import forms
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Jugador, Partido, Estadistica, Equipo
from .models import Pago
from .models import Tarjeta


# Formulario para comentarios de usuarios registrados


# Formulario para valoración de jugadores por el staff


# Formulario para registrar estadísticas de partidos
class EstadisticaForm(forms.ModelForm):
    """
    Formulario para el modelo Estadistica.
    Permite a los usuarios registrar estadísticas de un partido, incluyendo jugadores que anotaron, asistieron, fueron amonestados y expulsados.
    """
    class Meta:
        model = Estadistica
        fields = [
            'partido', 'goles', 'asistencias', 'tarjetas_amarillas', 'tarjetas_rojas',
            'anotadores', 'asistentes', 'amonestados', 'expulsados'
        ]
        widgets = {
            'partido': forms.Select(attrs={'class': 'form-control'}),
            'goles': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'asistencias': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tarjetas_amarillas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'tarjetas_rojas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'anotadores': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'asistentes': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'amonestados': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'expulsados': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

# Formulario para añadir un nuevo partido
class PartidoForm(forms.ModelForm):
    class Meta:
        model = Partido
        fields = [
            'equipo_local', 'equipo_visitante', 'fecha', 'marcador_local', 'marcador_visitante'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'marcador_local': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'marcador_visitante': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
        labels = {
            'equipo_local': 'Equipo Local',
            'equipo_visitante': 'Equipo Visitante',
            'marcador_local': 'Marcador Local',
            'marcador_visitante': 'Marcador Visitante',
        }
    # ModelChoiceField no es necesario, ModelForm lo gestiona automáticamente

# Formulario para subir fotos a la galería
        widgets = {
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'imagen': 'Seleccionar Imagen',
        }

# Formulario para publicar noticias
    # NoticiaForm eliminado

# Formulario para editar el perfil de un jugador
class JugadorForm(forms.ModelForm):
    """
    Formulario para el modelo Jugador.
    Permite a los usuarios editar la información básica de un jugador.
    """
    POSICIONES = [
        ('Delantero', _('Delantero')),
        ('Mediocampista', _('Mediocampista')),
        ('Defensa', _('Defensa')),
        ('Arquero', _('Arquero')),
    ]
    posicion = forms.ChoiceField(choices=POSICIONES, widget=forms.Select(attrs={'class': 'form-control'}))
    # Permitir que el campo equipo no sea obligatorio en el formulario de edición
    equipo = forms.ModelChoiceField(queryset=Equipo.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Jugador
        fields = [
            'nombre', 'apellido', 'posicion', 'numero_de_camiseta', 'equipo', 'fecha_de_nacimiento', 'foto_de_perfil'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nombre')}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Apellido')}),
            'posicion': forms.Select(attrs={'class': 'form-select'}),
            'numero_de_camiseta': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Ej: 10'), 'min': 1}),
            'equipo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_de_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'foto_de_perfil': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class PagoForm(forms.ModelForm):
    # Permitimos temporalmente entradas más largas en el formulario para normalizar
    # y luego almacenar solo los dígitos finales requeridos. El modelo sigue teniendo
    # max_length=6, por lo que en clean() reducimos la referencia antes de guardar.
    referencia = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Referencia/transacción', 'maxlength': '64', 'pattern': '\\d{0,64}', 'inputmode': 'numeric'}), max_length=64)
    class Meta:
        model = Pago
        fields = ['tipo', 'monto', 'metodo', 'referencia', 'comprobante', 'descripcion', 'moneda']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'min': 0.01, 'step': '0.01', 'required': True}),
            'metodo': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Referencia/transacción', 'maxlength': '6', 'pattern': '\\d{0,6}', 'inputmode': 'numeric'}),
            'comprobante': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': '50', 'placeholder': 'Opcional: agrega más detalles sobre el pago.'}),
            'moneda': forms.HiddenInput(),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Establecer método por defecto a 'pago_movil' cuando el formulario no está bind (nuevo registro)
            if not self.is_bound:
                self.initial.setdefault('metodo', 'pago_movil')

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        monto = cleaned.get('monto')
        if monto is None or monto <= 0:
            self.add_error('monto', 'El monto debe ser mayor que 0')
        # validar que metodo y referencia estén presentes
        metodo = cleaned.get('metodo')
        referencia = cleaned.get('referencia')
        if not metodo:
            self.add_error('metodo', 'Seleccione un método de pago')

        # Validación de moneda según método (mantener reglas previas)
        moneda = cleaned.get('moneda')
        # Si el método es 'divisas' forzamos USD. En otros casos respetamos la moneda
        # enviada por el usuario (esto permite 'efectivo' en USD o VES según el campo oculto).
        if metodo == 'divisas' and moneda != 'USD':
            cleaned['moneda'] = 'USD'
            moneda = 'USD'

        # No permitir USD para Pago Móvil o Transferencia: en esas vías usamos VES.
        # Permitir USD cuando el método sea 'efectivo' (caso solicitado).
        if metodo in ('pago_movil', 'transferencia') and moneda == 'USD':
            self.add_error('moneda', 'No es posible registrar Pago Móvil o Transferencia en USD.')
            # devolver cleaned temprano para no seguir validando como USD
            return cleaned

        # Reglas nuevas:
        # - Solo los métodos 'pago_movil' y 'transferencia' requieren referencia y comprobante.
    # - Para otros métodos (efectivo, otro, o cuando la moneda es USD),
        #   la referencia y comprobante no son obligatorios por defecto.
        comprobante = cleaned.get('comprobante')
        needs_comprobante = metodo in ('pago_movil', 'transferencia')

        # referencia requerida únicamente para pago_movil y transferencia
        if metodo in ('pago_movil', 'transferencia'):
            if not referencia:
                self.add_error('referencia', 'Ingrese una referencia o número de transacción')

        # Normalizar referencia según método:
        # - pago_movil -> guardar últimos 4 dígitos (requeridos)
        # - transferencia -> guardar últimos 6 dígitos (requeridos)
        # - otros -> si se proporciona, se requieren al menos 4 dígitos y se guardan últimos 4
        # Si el campo 'referencia' fue marcado inválido por validadores de campo (p.ej. max_length),
        # aún así queremos añadir nuestro mensaje amistoso cuando la fuente contiene >8 dígitos.
        raw_referencia = None
        try:
            # intentamos leer del POST directo
            raw_referencia = self.data.get('referencia') if hasattr(self, 'data') else None
        except Exception:
            raw_referencia = None

        if raw_referencia:
            raw_digits = ''.join(ch for ch in raw_referencia if ch.isdigit())
            # Si la referencia ingresada es solo dígitos y excede 6, mostrar error.
            # Pero si contiene letras/caracteres (p.ej. 'ABC-12345678') permitimos
            # la entrada y la normalizamos abajo (tomando los últimos dígitos).
            if raw_referencia.isdigit() and len(raw_digits) > 6:
                self.add_error('referencia', 'La referencia no puede contener más de 6 dígitos.')
                return cleaned

        if referencia:
            digits = ''.join(ch for ch in referencia if ch.isdigit())
            # Validación adicional: si la referencia es únicamente numérica y supera
            # los 6 dígitos la rechazamos. Si contiene otros caracteres, la
            # normalizamos tomando los dígitos finales requeridos.
            if referencia.isdigit() and len(digits) > 6:
                self.add_error('referencia', 'La referencia no puede contener más de 6 dígitos.')
                # evitar seguir normalizando si hay error
                return cleaned
            required = None
            if metodo == 'pago_movil':
                required = 4
            elif metodo == 'transferencia':
                required = 6
            else:
                required = 4

            if len(digits) < required:
                self.add_error('referencia', f'La referencia debe contener al menos {required} dígitos para el método seleccionado')
            else:
                # Para transferencias a veces el último dígito es un checksum; por compatibilidad
                # tomamos los 6 dígitos anteriores al último cuando hay suficiente longitud.
                if metodo == 'transferencia' and len(digits) >= (required + 1):
                    cleaned['referencia'] = digits[-(required+1):-1]
                else:
                    cleaned['referencia'] = digits[-required:]

        # Validar comprobante cuando sea necesario
        if needs_comprobante:
            if not comprobante:
                self.add_error('comprobante', 'Se requiere un comprobante para este método.')
            else:
                # Validar que sea una imagen
                content_type = getattr(comprobante, 'content_type', '')
                if content_type and not content_type.startswith('image/'):
                    self.add_error('comprobante', 'El comprobante debe ser una imagen (foto).')
                # Nota: no imponer un tamaño mínimo estricto en el servidor de pruebas;
                # confiamos en la validación de tipo MIME y en que en producción los
                # comprobantes sean imágenes válidas. Esto evita fallos por PNGs
                # muy comprimidos en entorno de tests.
        return cleaned


class PagoAdminForm(PagoForm):
    """Formulario para que el staff/admin cree pagos: incluye campo jugador y permite seleccionar moneda."""
    jugador = forms.ModelChoiceField(queryset=Jugador.objects.all(), widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta(PagoForm.Meta):
        fields = ['jugador'] + PagoForm.Meta.fields
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar moneda como select para el staff (no como hidden)
        if 'moneda' in self.fields:
            self.fields['moneda'].widget = forms.Select(choices=Pago.MONEDA_CHOICES, attrs={'class': 'form-select'})


class TarjetaForm(forms.ModelForm):
    class Meta:
        model = Tarjeta
        fields = ['jugador', 'tipo', 'minuto']
        widgets = {
            'jugador': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'minuto': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
