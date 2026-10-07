import pytest
from django.contrib import admin
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
def test_every_admin_page_opens(demo, lang):
    client = Client(HTTP_ACCEPT_LANGUAGE=lang)
    client.force_login(User.objects.get(username="admin"))
    for model in admin.site._registry:
        opts = model._meta
        for view in ("changelist", "add"):
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_{view}")
            assert client.get(url).status_code == 200, url
