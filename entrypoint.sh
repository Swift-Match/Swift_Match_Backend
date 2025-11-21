#!/bin/bash

echo "🚀 Aguardando banco de dados..."
/usr/local/bin/wait-for-it.sh db:5432 --timeout=60 --strict -- echo "Database UP! ✔️"

# Não há migração aqui!
exec "$@"