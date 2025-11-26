from django.apps import AppConfig

class RankingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rankings'

    def ready(self):
        # importa o módulo signals para registrar receivers
        try:
            import apps.rankings.signals  # noqa: F401
        except Exception:
            # opcional: logar erro para debug
            import logging
            logging.getLogger(__name__).exception("Falha importando apps.rankings.signals")
