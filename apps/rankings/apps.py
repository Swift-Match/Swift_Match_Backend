from django.apps import AppConfig


class RankingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rankings"

    def ready(self):
        try:
            pass
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Falha importando apps.rankings.signals"
            )
