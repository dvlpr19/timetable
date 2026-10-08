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


def test_change_password(user):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.post(
        reverse("change-password"),
        {"current_password": "talaba123", "new_password": "Yangi-parol-2026"},
        format="json",
    )
    assert resp.status_code == 204
    user.refresh_from_db()
    assert user.check_password("Yangi-parol-2026")


def test_change_password_rejects_wrong_current(user):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.post(
        reverse("change-password"),
        {"current_password": "wrong", "new_password": "Yangi-parol-2026"},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )
    assert resp.status_code == 400
    assert resp.data["current_password"] == ["Current password is incorrect."]
    user.refresh_from_db()
    assert user.check_password("talaba123")


def test_change_password_requires_auth():
    assert APIClient().post(reverse("change-password"), {}).status_code == 401


def test_me_contact_details_are_editable(user):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.patch(
        reverse("me"), {"email": "aziza@example.uz", "phone": "+998 90 123-45-67"}, format="json"
    )
    assert resp.status_code == 200
    user.refresh_from_db()
    assert (user.email, user.phone) == ("aziza@example.uz", "+998 90 123-45-67")


def test_me_rejects_bad_phone(user):
    client = APIClient()
    client.force_authenticate(user)
    resp = client.patch(reverse("me"), {"phone": "call me"}, format="json")
    assert resp.status_code == 400
    assert "phone" in resp.data


def test_my_stats_for_staff_without_person(user):
    user.role = Role.ADMIN
    user.save()
    client = APIClient()
    client.force_authenticate(user)
    resp = client.get(reverse("my-stats"))
    assert resp.status_code == 200
    assert resp.data["kind"] == "staff"
    assert {"groups", "teachers", "rooms"} <= resp.data.keys()
