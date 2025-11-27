#!/bin/bash

if [ -z "$RENDER" ]; then
    echo "🚀 Aguardando banco de dados local (db:5432)..."
    /usr/local/bin/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "Database UP! ✔️"
    exec "$@" 
else
    echo "Ambiente de Produção (Render) detectado."
    echo "--> Executando script de PRODUÇÃO (run_prod.sh) [COM MIGRAÇÃO E CELERY]"
    exec /app/run_prod.sh
fi