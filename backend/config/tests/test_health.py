import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health():
    resp = APIClient().get(reverse("health"))
    assert resp.status_code == 200
    assert resp.data == {"status": "ok"}


def test_celery_ping_task_runs_eagerly():
    from config.celery import ping

    assert ping.apply().get() == "pong"
