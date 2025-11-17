#!/bin/bash
echo "🚀 Aguardando banco de dados..."
sleep 5

echo "📌 Rodando migrations..."
python manage.py migrate

echo "🧪 Rodando testes..."
python manage.py test

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Testes passaram! Iniciando servidor..."
    python manage.py runserver 0.0.0.0:8000
else
    echo "❌ Testes falharam! Servidor não será iniciado."
    exit 1
fi
