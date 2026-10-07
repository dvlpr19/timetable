import io

import pytest
from django.db import transaction


@pytest.fixture(scope="module")
def demo(django_db_setup, django_db_blocker):
    """The full demo dataset, built once per test module and rolled back afterwards."""
    from apps.academics.seed.builder import build_demo

    with django_db_blocker.unblock(), transaction.atomic():
        summary = build_demo(io.StringIO())
        yield summary
        transaction.set_rollback(True)


@pytest.fixture(autouse=True)
def _celery_eager():
    """Tasks run in-process in tests (no broker)."""
    from config.celery import app

    app.conf.task_always_eager = True
    yield
    app.conf.task_always_eager = False
