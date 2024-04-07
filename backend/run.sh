#!/bin/sh
echo "Running migrations..."
python manage.py makemigrations;
python manage.py migrate;

echo "Collecting static files..."
python manage.py collectstatic --noinput;

echo "Loading initial data..."
python manage.py loaddata users.json;

echo "Starting Celery worker..."
celery -A backend worker -l info --pool=solo --without-mingle --without-gossip &

echo "Starting Celery beat..."
celery -A backend beat --loglevel=info &

echo "Copying static files..."
cp -r /app/collected_static/. /backend_static/static/

echo "Starting Gunicorn..."
gunicorn --bind 0:8000 backend.wsgi;