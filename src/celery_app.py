from celery import Celery

from src.config import settings
from src.services.aws import get_sqs_client_kwargs

app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=None,
)

app.conf.update(
    broker_transport_options={
        **get_sqs_client_kwargs(),
    }
)

app.set_default()
app.autodiscover_tasks()

from src import tasks  # noqa
