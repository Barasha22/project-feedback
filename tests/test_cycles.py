from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from cycles.models import FeedbackCycle
from projects.models import Membership, Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="Owner-pass-1963!")


@pytest.fixture
def member():
    return User.objects.create_user(username="member", password="Member-pass-1963!")


@pytest.fixture
def outsider():
    return User.objects.create_user(username="outsider", password="Outsider-pass-1963!")


@pytest.fixture
def project(owner, member):
    project = Project.objects.create(name="Apollo", owner=owner)
    Membership.objects.create(
        project=project, user=owner, role=Membership.Role.FACILITATOR
    )
    Membership.objects.create(project=project, user=member)
    return project


def cycle_data(facilitator):
    opens_at = timezone.now() + timedelta(days=1)
    closes_at = opens_at + timedelta(days=5)
    return {
        "week_start": date.today() + timedelta(days=1),
        "opens_at": opens_at.strftime("%Y-%m-%dT%H:%M"),
        "closes_at": closes_at.strftime("%Y-%m-%dT%H:%M"),
        "facilitator": facilitator.pk,
    }


def create_cycle(project, facilitator, status=FeedbackCycle.Status.COLLECTING):
    opens_at = timezone.now() + timedelta(days=1)
    return FeedbackCycle.objects.create(
        project=project,
        week_start=date.today() + timedelta(days=1),
        opens_at=opens_at,
        closes_at=opens_at + timedelta(days=5),
        facilitator=facilitator,
        status=status,
    )


def test_project_facilitator_can_create_cycle_for_member(
    client, owner, member, project
):
    client.force_login(owner)

    response = client.post(
        reverse("cycles:create", args=(project.pk,)), cycle_data(member)
    )

    assert response.status_code == 302
    cycle = FeedbackCycle.objects.get(project=project)
    assert cycle.facilitator == member
    assert cycle.status == FeedbackCycle.Status.COLLECTING


def test_member_cannot_create_cycle(client, member, project):
    client.force_login(member)

    response = client.post(
        reverse("cycles:create", args=(project.pk,)), cycle_data(member)
    )

    assert response.status_code == 404
    assert not FeedbackCycle.objects.exists()


def test_selected_facilitator_must_be_project_member(client, owner, outsider, project):
    client.force_login(owner)

    response = client.post(
        reverse("cycles:create", args=(project.pk,)), cycle_data(outsider)
    )

    assert response.status_code == 200
    assert "Select a valid choice" in response.content.decode()
    assert not FeedbackCycle.objects.exists()


def test_only_one_collecting_cycle_per_project(project, owner):
    create_cycle(project, owner)

    with pytest.raises(IntegrityError):
        create_cycle(project, owner)


def test_closed_cycle_allows_new_collecting_cycle(project, owner):
    create_cycle(project, owner, status=FeedbackCycle.Status.CLOSED)

    second = create_cycle(project, owner)

    assert second.status == FeedbackCycle.Status.COLLECTING
    assert FeedbackCycle.objects.filter(project=project).count() == 2


def test_duplicate_collecting_cycle_shows_form_error(client, owner, project):
    create_cycle(project, owner)
    client.force_login(owner)

    response = client.post(
        reverse("cycles:create", args=(project.pk,)), cycle_data(owner)
    )

    assert response.status_code == 200
    assert "already has a cycle collecting feedback" in response.content.decode()
    assert FeedbackCycle.objects.filter(project=project).count() == 1


def test_cycle_facilitator_can_close_cycle(client, member, project):
    cycle = create_cycle(project, member)
    client.force_login(member)

    response = client.post(reverse("cycles:close", args=(cycle.pk,)))

    assert response.status_code == 302
    cycle.refresh_from_db()
    assert cycle.status == FeedbackCycle.Status.CLOSED


def test_project_owner_cannot_close_another_cycle_facilitators_cycle(
    client, owner, member, project
):
    cycle = create_cycle(project, member)
    client.force_login(owner)

    response = client.post(reverse("cycles:close", args=(cycle.pk,)))

    assert response.status_code == 404
    cycle.refresh_from_db()
    assert cycle.status == FeedbackCycle.Status.COLLECTING


def test_close_is_post_only_and_idempotent(client, owner, project):
    cycle = create_cycle(project, owner)
    client.force_login(owner)
    url = reverse("cycles:close", args=(cycle.pk,))

    assert client.get(url).status_code == 405
    assert client.post(url).status_code == 302
    assert client.post(url).status_code == 302
    cycle.refresh_from_db()
    assert cycle.status == FeedbackCycle.Status.CLOSED


def test_create_and_close_require_csrf(owner, project):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(owner)

    assert (
        csrf_client.post(
            reverse("cycles:create", args=(project.pk,)), cycle_data(owner)
        ).status_code
        == 403
    )
    cycle = create_cycle(project, owner)
    assert (
        csrf_client.post(reverse("cycles:close", args=(cycle.pk,))).status_code == 403
    )


def test_close_time_must_follow_open_time(client, owner, project):
    client.force_login(owner)
    data = cycle_data(owner)
    data["closes_at"] = data["opens_at"]

    response = client.post(reverse("cycles:create", args=(project.pk,)), data)

    assert response.status_code == 200
    assert not FeedbackCycle.objects.exists()
