from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "docker_control",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_soft_time_limit=300,
    task_time_limit=600,
)

if __name__ == "__main__":
    celery_app.start()