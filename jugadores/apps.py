from django.apps import AppConfig


class JugadoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jugadores'

    def ready(self):
        # Importa el archivo de señales para que Django lo cargue.
        # El try/except evita errores durante operaciones sin Django completo.
        try:
            import jugadores.signals  # noqa
        except Exception:
            pass
