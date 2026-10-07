#!/bin/sh
set -e
python manage.py compilemessages -v 0
python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:8000
