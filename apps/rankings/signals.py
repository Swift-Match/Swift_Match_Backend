# apps/rankings/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AlbumRanking, TrackRanking
from .tasks import run_global_ranking_calculation
import logging

logger = logging.getLogger(__name__)

def enqueue_global_ranking_task():
    try:
        # delay() -> assíncrono; use apply_async if quiser opções
        run_global_ranking_calculation.delay()
        logger.info("Enfileirada run_global_ranking_calculation via signal.")
    except Exception:
        logger.exception("Falha ao enfileirar run_global_ranking_calculation via signal.")

# Dispara quando um AlbumRanking for criado/atualizado/apagado
@receiver(post_save, sender=AlbumRanking)
def album_ranking_saved(sender, instance, created, **kwargs):
    logger.debug("Signal: AlbumRanking saved id=%s created=%s", getattr(instance, 'id', None), created)
    enqueue_global_ranking_task()

@receiver(post_delete, sender=AlbumRanking)
def album_ranking_deleted(sender, instance, **kwargs):
    logger.debug("Signal: AlbumRanking deleted id=%s", getattr(instance, 'id', None))
    enqueue_global_ranking_task()

# Dispara também em modificações de TrackRanking (se necessário)
@receiver(post_save, sender=TrackRanking)
def track_ranking_saved(sender, instance, created, **kwargs):
    logger.debug("Signal: TrackRanking saved id=%s created=%s", getattr(instance, 'id', None), created)
    enqueue_global_ranking_task()

@receiver(post_delete, sender=TrackRanking)
def track_ranking_deleted(sender, instance, **kwargs):
    logger.debug("Signal: TrackRanking deleted id=%s", getattr(instance, 'id', None))
    enqueue_global_ranking_task()
