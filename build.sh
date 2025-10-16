#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Um comando futuro para migrações de banco de dados poderia ir aqui
# python manage.py migrate