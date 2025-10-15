# jugadores/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Equipo, Jugador, Partido, Estadistica, Torneo, VotacionJugadorPartido
from .models import Pago
from .models import Tarjeta


class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
    filter_horizontal = ('torneos',)
    verbose_name = _('Equipo')


class JugadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'posicion', 'equipo')
    search_fields = ('nombre', 'apellido', 'equipo__nombre')


class PartidoAdmin(admin.ModelAdmin):
    list_display = ('torneo', 'equipo_local', 'equipo_visitante', 'fecha')
    list_filter = ('torneo',)


admin.site.register(Equipo, EquipoAdmin)
admin.site.register(Jugador, JugadorAdmin)
admin.site.register(Partido, PartidoAdmin)
admin.site.register(Estadistica)
admin.site.register(Torneo)
admin.site.register(VotacionJugadorPartido)
admin.site.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'jugador', 'tipo', 'monto', 'estado', 'fecha')
    list_filter = ('tipo', 'estado', 'fecha')
    search_fields = ('jugador__nombre', 'jugador__apellido', 'referencia')
    actions = ['marcar_aprobado', 'marcar_rechazado']

    def marcar_aprobado(self, request, queryset):
        updated = queryset.update(estado='aprobado')
        self.message_user(request, f'{updated} pagos marcados como aprobados.')
    marcar_aprobado.short_description = 'Marcar seleccionados como Aprobado'

    def marcar_rechazado(self, request, queryset):
        updated = queryset.update(estado='rechazado')
        self.message_user(request, f'{updated} pagos marcados como rechazados.')
    marcar_rechazado.short_description = 'Marcar seleccionados como Rechazado'


admin.site.unregister(Pago) if hasattr(admin.site, 'unregister') else None
admin.site.register(Pago, PagoAdmin)


class TarjetaAdmin(admin.ModelAdmin):
    list_display = ('partido', 'jugador', 'tipo', 'minuto', 'fecha', 'anulada', 'motivo_anulacion')
    list_filter = ('tipo', 'partido', 'anulada')
    search_fields = ('jugador__nombre', 'jugador__apellido', 'partido__torneo__nombre')
    actions = ['eliminar_tarjetas_seleccionadas']

    def eliminar_tarjetas_seleccionadas(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} tarjetas eliminadas.')
    eliminar_tarjetas_seleccionadas.short_description = 'Eliminar tarjetas seleccionadas'

    def anular_tarjetas(self, request, queryset):
        updated = queryset.update(anulada=True, motivo_anulacion='Anulada desde admin')
        self.message_user(request, f'{updated} tarjetas marcadas como anuladas.')
    anular_tarjetas.short_description = 'Marcar como anuladas'

    def revertir_anulacion(self, request, queryset):
        updated = queryset.update(anulada=False, motivo_anulacion=None)
        self.message_user(request, f'{updated} anulaciones revertidas.')
    revertir_anulacion.short_description = 'Revertir anulación'

    actions = ['eliminar_tarjetas_seleccionadas', 'anular_tarjetas', 'revertir_anulacion']

admin.site.register(Tarjeta, TarjetaAdmin)

