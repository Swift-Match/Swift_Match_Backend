from config.celery import app
from .utils import calculate_global_ranking, calculate_group_internal_coherence
from celery import shared_task

@app.task
def run_global_ranking_calculation():
    """
    Tarefa agendada para calcular e atualizar o ranking global de países.
    """
    calculate_global_ranking()
    return "Cálculo global de ranking concluído com sucesso."

