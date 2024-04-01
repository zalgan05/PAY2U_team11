import os
from django.conf import settings

from celery import Celery


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE', 'backend.settings'
)

VERSION_API = settings.VERSION_API

app = Celery('backend', include=[f'api.v{VERSION_API}.tasks'])
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True
app.autodiscover_tasks()
