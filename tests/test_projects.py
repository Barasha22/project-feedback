from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from projects.models import Membership, Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="Owner-pass-1963!")


@pytest.fixture
def member():
    return User.objects.create_user(username="member", password="Member-pass-1963!")


@pytest.fixture
def project(owner):
    project = Project.objects.create(name="Apollo", owner=owner)
    Membership.objects.create(
        project=project, user=owner, role=Membership.Role.FACILITATOR
    )
    return project


def test_project_creation_adds_owner_facilitator_membership(client, owner):
    client.force_login(owner)

    response = client.post(reverse("projects:create"), {"name": "Apollo"})

    project = Project.objects.get(name="Apollo")
    assert response.status_code == 302
    assert response.url == reverse("projects:detail", args=(project.pk,))
    assert project.owner == owner
    assert Membership.objects.filter(
        project=project, user=owner, role=Membership.Role.FACILITATOR
    ).exists()


def test_project_creation_rolls_back_when_membership_creation_fails(client, owner):
    client.force_login(owner)

    with patch("projects.views.Membership.objects.create", side_effect=IntegrityError):
        with pytest.raises(IntegrityError):
            client.post(reverse("projects:create"), {"name": "Apollo"})

    assert not Project.objects.filter(name="Apollo").exists()


def test_project_list_contains_only_memberships(client, owner, member, project):
    hidden = Project.objects.create(name="Hidden", owner=member)
    Membership.objects.create(
        project=hidden, user=member, role=Membership.Role.FACILITATOR
    )
    client.force_login(owner)

    response = client.get(reverse("projects:list"))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Apollo" in content
    assert "Hidden" not in content


def test_project_detail_is_hidden_from_non_members(client, member, project):
    client.force_login(member)

    response = client.get(reverse("projects:detail", args=(project.pk,)))

    assert response.status_code == 404


def test_join_requires_login(client, project):
    response = client.get(reverse("join-project", args=(project.join_token,)))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_join_get_is_confirmation_and_does_not_mutate(client, member, project):
    client.force_login(member)

    response = client.get(reverse("join-project", args=(project.join_token,)))

    assert response.status_code == 200
    assert "Join Apollo?" in response.content.decode()
    assert not Membership.objects.filter(project=project, user=member).exists()


def test_join_post_creates_member_and_is_idempotent(client, member, project):
    client.force_login(member)
    url = reverse("join-project", args=(project.join_token,))

    first = client.post(url)
    second = client.post(url)

    assert first.status_code == 302
    assert second.status_code == 302
    membership = Membership.objects.get(project=project, user=member)
    assert membership.role == Membership.Role.MEMBER
    assert Membership.objects.filter(project=project, user=member).count() == 1


def test_join_does_not_downgrade_existing_facilitator(client, member, project):
    Membership.objects.create(
        project=project, user=member, role=Membership.Role.FACILITATOR
    )
    client.force_login(member)

    client.post(reverse("join-project", args=(project.join_token,)))

    membership = Membership.objects.get(project=project, user=member)
    assert membership.role == Membership.Role.FACILITATOR


def test_membership_is_unique(project, member):
    Membership.objects.create(project=project, user=member)

    with pytest.raises(IntegrityError):
        Membership.objects.create(project=project, user=member)


def test_owner_can_rotate_token_and_old_link_stops_working(
    client, owner, member, project
):
    old_token = project.join_token
    client.force_login(owner)

    response = client.post(reverse("projects:rotate-join-token", args=(project.pk,)))

    assert response.status_code == 302
    project.refresh_from_db()
    assert project.join_token != old_token

    client.force_login(member)
    assert client.post(reverse("join-project", args=(old_token,))).status_code == 404
    assert (
        client.post(reverse("join-project", args=(project.join_token,))).status_code
        == 302
    )
    assert Membership.objects.filter(project=project, user=member).exists()


def test_rotation_requires_post_and_owner(client, owner, member, project):
    url = reverse("projects:rotate-join-token", args=(project.pk,))
    client.force_login(owner)
    assert client.get(url).status_code == 405

    client.force_login(member)
    assert client.post(url).status_code == 404


def test_join_and_rotation_require_csrf(owner, member, project):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(member)
    join_url = reverse("join-project", args=(project.join_token,))
    assert csrf_client.post(join_url).status_code == 403

    csrf_client.force_login(owner)
    rotate_url = reverse("projects:rotate-join-token", args=(project.pk,))
    assert csrf_client.post(rotate_url).status_code == 403
