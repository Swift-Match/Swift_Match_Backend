#!/bin/bash
# run_web.sh 

echo "📌 Rodando migrations..."
python manage.py migrate --noinput

echo "🧪 Rodando testes..."
pytest -q --ds=config.settings.dev

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Testes passaram! Iniciando servidor..."
    # Use 'exec' para iniciar o processo Gunicorn/Runserver como processo principal (PID 1)
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "❌ Testes falharam! Servidor não será iniciado."
    exit 1
fi