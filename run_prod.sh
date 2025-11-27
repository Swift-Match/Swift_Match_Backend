#!/bin/bash

echo "--> Aplicando migrações no Supabase..."
python manage.py migrate --noinput

echo "--> Iniciando Celery Worker e Beat em segundo plano..."
celery -A config worker -l info &
celery -A config beat -l info -s /tmp/celerybeat-schedule &

echo "--> Iniciando Gunicorn em primeiro plano (Sem 'exec')..."
# REMOVA O 'exec' AQUI!
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT