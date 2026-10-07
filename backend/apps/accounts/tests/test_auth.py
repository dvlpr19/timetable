import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(
        username="talaba", password="talaba123", first_name="Aziza", last_name="Karimova"
    )


def test_login_returns_tokens(user):
    resp = APIClient().post(
        reverse("login"), {"username": "talaba", "password": "talaba123"}, format="json"
    )
    assert resp.status_code == 200
    assert {"access", "refresh"} <= resp.data.keys()


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("uz", "Login yoki parol noto'g'ri."),
        ("ru", "Неверный логин или пароль."),
        ("en", "Incorrect login or password."),
    ],
)
def test_login_error_follows_accept_language(user, lang, expected):
    resp = APIClient().post(
        reverse("login"),
        {"username": "talaba", "password": "wrong"},
        format="json",
        HTTP_ACCEPT_LANGUAGE=lang,
    )
    assert resp.status_code == 401
    assert resp.data["detail"] == expected


def test_me_requires_auth():
    assert APIClient().get(reverse("me")).status_code == 401


def test_me_language_update_persists(user):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.patch(reverse("me"), {"language": "ru"}, format="json")
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.language == "ru"
    assert user.language_auto is False


def test_me_cannot_change_role(user):
    client = APIClient()
    client.force_authenticate(user)
    client.patch(reverse("me"), {"role": Role.ADMIN}, format="json")
    user.refresh_from_db()
    assert user.role == Role.TALABA


def test_me_rejects_unknown_language(user):
    client = APIClient()
    client.force_authenticate(user)
    assert client.patch(reverse("me"), {"language": "de"}, format="json").status_code == 400
