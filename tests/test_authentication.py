import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def signup_data(**overrides):
    data = {
        "username": "river",
        "display_name": "River Song",
        "password1": "Tardis-River-1963!",
        "password2": "Tardis-River-1963!",
    }
    data.update(overrides)
    return data


def test_signup_creates_and_authenticates_user(client):
    response = client.post(reverse("accounts:signup"), signup_data())

    assert response.status_code == 302
    assert response.url == reverse("home")
    user = User.objects.get(username="river")
    assert user.first_name == "River Song"
    assert user.email == ""
    assert user.password != "Tardis-River-1963!"
    assert user.check_password("Tardis-River-1963!")
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    [
        ({"display_name": ""}, "This field is required"),
        ({"password2": "Different-password-1963!"}, "password fields didn’t match"),
        (
            {"password1": "password", "password2": "password"},
            "This password is too common",
        ),
    ],
)
def test_invalid_signup_shows_errors_without_creating_user(
    client, overrides, expected_error
):
    response = client.post(reverse("accounts:signup"), signup_data(**overrides))

    assert response.status_code == 200
    assert expected_error in response.content.decode()
    assert not User.objects.filter(username="river").exists()


def test_duplicate_username_shows_error(client):
    User.objects.create_user(username="river", password="Existing-pass-1963!")

    response = client.post(reverse("accounts:signup"), signup_data())

    assert response.status_code == 200
    assert "A user with that username already exists" in response.content.decode()
    assert User.objects.filter(username="river").count() == 1


def test_signup_and_login_forms_do_not_expose_email(client):
    signup_response = client.get(reverse("accounts:signup"))
    login_response = client.get(reverse("login"))

    assert 'name="email"' not in signup_response.content.decode()
    assert 'name="email"' not in login_response.content.decode()


def test_registered_user_can_log_in(client):
    user = User.objects.create_user(username="river", password="Existing-pass-1963!")

    response = client.post(
        reverse("login"),
        {"username": "river", "password": "Existing-pass-1963!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("home")
    assert client.session["_auth_user_id"] == str(user.pk)


def test_invalid_credentials_do_not_authenticate(client):
    User.objects.create_user(username="river", password="Existing-pass-1963!")

    response = client.post(
        reverse("login"), {"username": "river", "password": "incorrect"}
    )

    assert response.status_code == 200
    assert "Please enter a correct username and password" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_logout_requires_post(client):
    user = User.objects.create_user(username="river", password="Existing-pass-1963!")
    client.force_login(user)

    response = client.get(reverse("logout"))

    assert response.status_code == 405
    assert client.session["_auth_user_id"] == str(user.pk)


def test_logout_requires_csrf_and_redirects_home():
    user = User.objects.create_user(username="river", password="Existing-pass-1963!")
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(user)

    rejected = csrf_client.post(reverse("logout"))
    assert rejected.status_code == 403

    csrf_client.get(reverse("home"))
    token = csrf_client.cookies["csrftoken"].value
    response = csrf_client.post(reverse("logout"), {"csrfmiddlewaretoken": token})

    assert response.status_code == 302
    assert response.url == reverse("home")
    assert "_auth_user_id" not in csrf_client.session


def test_password_reset_route_is_not_mounted(client):
    response = client.get("/accounts/password_reset/")

    assert response.status_code == 404
