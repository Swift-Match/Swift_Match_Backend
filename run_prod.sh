#!/bin/sh

# run_prod.sh

# 1. Aplicar Migrações do Banco de Dados
echo "--> Aplicando migrações no Supabase..."
python manage.py migrate --noinput

# Verificar se a migração falhou.
if [ $? -ne 0 ]; then
    echo "Falha na aplicação das migrações. Saindo."
    exit 1
fi

# 2. Iniciar o Servidor Web Gunicorn (produção)
echo "--> Iniciando Gunicorn em $PORT..."
# Usa o Gunicorn e a porta fornecida pelo Render
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT