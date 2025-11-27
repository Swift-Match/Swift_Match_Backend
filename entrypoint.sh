#!/bin/bash

if host db; then
    echo "🚀 Aguardando banco de dados local (db:5432)..."
    /usr/local/bin/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "Database UP! ✔️"
else
    echo "Ambiente de Produção/Externo detectado. Pulando wait-for-it."
fi

if [[ "$1" == "gunicorn" ]]; then
    echo "--> Executando script de PRODUÇÃO (run_prod.sh)..."
    exec /app/run_prod.sh
    
elif [[ "$1" == "celery" ]]; then
    echo "--> Executando comando Celery Worker/Beat..."
    echo "--> Aplicando migrações antes de iniciar o Celery..."
    python manage.py migrate --noinput
    
    exec "$@" 

elif [[ "$1" == "/app/run_web.sh" ]]; then
    echo "--> Executando script de DESENVOLVIMENTO (run_web.sh)..."
    exec "$@" 
    
else
    echo "--> Executando comando padrão: $@"
    exec "$@"
fi