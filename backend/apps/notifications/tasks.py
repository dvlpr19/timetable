from celery import shared_task
from django.db import transaction

from . import service


@shared_task(name="notifications.announce_changes")
def announce_changes(schedule_id: int) -> int:
    return service.announce_changes(schedule_id)


@shared_task(name="notifications.announce_publication")
def announce_publication(schedule_id: int) -> int:
    return service.announce_publication(schedule_id)


@shared_task(name="notifications.announce_request")
def announce_request(request_id: int) -> int:
    from apps.scheduling.models import RescheduleRequest

    req = RescheduleRequest.objects.select_related(
        "teacher__user", "entry__lesson_time", "entry__assignment__subject"
    ).get(pk=request_id)
    return service.announce_request_answer(req)


@shared_task(name="notifications.reminders")
def send_reminders() -> int:
    return service.send_reminders()


@shared_task(name="notifications.daily_digest")
def send_daily_digest() -> int:
    return service.send_daily_digest()


def after_commit(task, *args) -> None:
    """Queue a task once the current transaction is saved (the worker must see the data)."""
    transaction.on_commit(lambda: task.delay(*args))
