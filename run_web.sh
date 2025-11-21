#!/bin/bash
# run_web.sh

# Garante que o módulo de configurações está exportado para comandos futuros
export DJANGO_SETTINGS_MODULE=config.settings.dev

echo "📌 Rodando migrations..."
python manage.py migrate --noinput

echo "🧪 Rodando testes com Cobertura de Código..."

pytest --cov=apps --cov-report=term -q

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Testes e Cobertura OK! Iniciando servidor..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "❌ Testes e/ou Cobertura falharam! Servidor não será iniciado."
    exit 1
fi