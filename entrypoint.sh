#!/bin/bash

if [ -z "$RENDER" ]; then
    echo "🚀 Aguardando banco de dados local (db:5432)..."
    /usr/local/bin/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "Database UP! ✔️"
else
    echo "Ambiente de Produção (Render) detectado. Pulando wait-for-it."
fi

echo "--> Executando comando de inicialização fornecido pela Render: $@"
exec "$@"