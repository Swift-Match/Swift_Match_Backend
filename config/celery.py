import os
from celery import Celery

# Define a configuração Django padrão para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('swift_match')

# Carrega as configurações do Django (o namespace CELEY_ evita conflito)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobre tarefas em todos os apps instalados
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')