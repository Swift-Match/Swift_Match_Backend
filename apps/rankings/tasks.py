from config.celery import app
from .utils import calculate_global_ranking


@app.task
def run_global_ranking_calculation():
    """
    Tarefa agendada para calcular e atualizar o ranking global de países.
    """
    calculate_global_ranking()
    return "Cálculo global de ranking concluído com sucesso."
