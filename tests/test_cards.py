from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from cycles.models import Card, FeedbackCycle
from projects.models import Membership, Project

pytestmark = pytest.mark.django_db


@pytest.fixture
def alice():
    return User.objects.create_user(username="alice", password="Alice-pass-1963!")


@pytest.fixture
def bob():
    return User.objects.create_user(username="bob", password="Bob-pass-1963!")


@pytest.fixture
def outsider():
    return User.objects.create_user(username="outsider", password="Other-pass-1963!")


@pytest.fixture
def cycle(alice, bob):
    project = Project.objects.create(name="Apollo", owner=alice)
    Membership.objects.create(
        project=project, user=alice, role=Membership.Role.FACILITATOR
    )
    Membership.objects.create(project=project, user=bob)
    opens_at = timezone.now() - timedelta(days=1)
    return FeedbackCycle.objects.create(
        project=project,
        week_start=date.today(),
        opens_at=opens_at,
        closes_at=opens_at + timedelta(days=7),
        facilitator=alice,
    )


def create_card(cycle, author, **overrides):
    values = {
        "category": Card.Category.START,
        "text": f"Card by {author.username}",
        "is_anonymous": False,
        "position": 0,
    }
    values.update(overrides)
    return Card.objects.create(cycle=cycle, author=author, **values)


def test_feedback_page_query_excludes_other_members_cards(client, alice, bob, cycle):
    create_card(cycle, alice, text="Alice private feedback")
    create_card(cycle, bob, text="Bob secret feedback")
    client.force_login(alice)

    response = client.get(reverse("cycles:feedback-cards", args=(cycle.pk,)))

    content = response.content.decode()
    assert response.status_code == 200
    assert "Alice private feedback" in content
    assert "Bob secret feedback" not in content


def test_non_member_cannot_view_feedback_page(client, outsider, cycle):
    client.force_login(outsider)

    response = client.get(reverse("cycles:feedback-cards", args=(cycle.pk,)))

    assert response.status_code == 404


@pytest.mark.parametrize("category", Card.Category.values)
def test_member_can_create_each_card_category(client, alice, cycle, category):
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-create", args=(cycle.pk, category)),
        {"text": f"A {category} card", "is_anonymous": "on"},
    )

    assert response.status_code == 302
    card = Card.objects.get(category=category)
    assert card.author == alice
    assert card.text == f"A {category} card"
    assert card.is_anonymous is True


def test_card_positions_increment_per_author_and_category(client, alice, cycle):
    client.force_login(alice)
    url = reverse("cycles:card-create", args=(cycle.pk, Card.Category.START))

    client.post(url, {"text": "First"})
    client.post(url, {"text": "Second"})

    assert list(
        Card.objects.filter(author=alice).values_list("position", flat=True)
    ) == [0, 1]


def test_htmx_create_returns_only_own_updated_column(client, alice, bob, cycle):
    create_card(cycle, bob, text="Never leak this")
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-create", args=(cycle.pk, Card.Category.START)),
        {"text": "Visible to Alice"},
        headers={"HX-Request": "true"},
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert 'id="cards-start"' in content
    assert "Visible to Alice" in content
    assert "Never leak this" not in content
    assert "<html" not in content


def test_invalid_htmx_create_returns_form_errors_without_card(client, alice, cycle):
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-create", args=(cycle.pk, Card.Category.START)),
        {"text": ""},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "This field is required" in response.content.decode()
    assert not Card.objects.exists()


def test_invalid_category_is_rejected(client, alice, cycle):
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-create", args=(cycle.pk, "INVALID")),
        {"text": "Nope"},
    )

    assert response.status_code == 404


def test_member_can_edit_own_card_over_htmx(client, alice, cycle):
    card = create_card(cycle, alice)
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-edit", args=(card.pk,)),
        {"text": "Updated", "is_anonymous": "on"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "Updated" in response.content.decode()
    card.refresh_from_db()
    assert card.text == "Updated"
    assert card.is_anonymous is True


def test_member_cannot_edit_or_delete_another_members_card(client, alice, bob, cycle):
    card = create_card(cycle, bob)
    client.force_login(alice)

    edit = client.post(reverse("cycles:card-edit", args=(card.pk,)), {"text": "Stolen"})
    delete = client.post(reverse("cycles:card-delete", args=(card.pk,)))

    assert edit.status_code == 404
    assert delete.status_code == 404
    assert Card.objects.filter(pk=card.pk, text="Card by bob").exists()


def test_htmx_delete_returns_updated_column(client, alice, cycle):
    card = create_card(cycle, alice)
    client.force_login(alice)

    response = client.post(
        reverse("cycles:card-delete", args=(card.pk,)),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "No start cards yet" in response.content.decode()
    assert not Card.objects.filter(pk=card.pk).exists()


@pytest.mark.parametrize("operation", ["create", "edit", "delete"])
def test_card_mutations_are_rejected_after_cycle_closes(
    client, alice, cycle, operation
):
    card = create_card(cycle, alice)
    cycle.status = FeedbackCycle.Status.CLOSED
    cycle.save(update_fields=("status",))
    client.force_login(alice)

    if operation == "create":
        url = reverse("cycles:card-create", args=(cycle.pk, Card.Category.START))
        response = client.post(url, {"text": "Late"})
    elif operation == "edit":
        response = client.post(
            reverse("cycles:card-edit", args=(card.pk,)), {"text": "Late edit"}
        )
    else:
        response = client.post(reverse("cycles:card-delete", args=(card.pk,)))

    assert response.status_code == 409
    assert Card.objects.filter(pk=card.pk).exists()
    assert not Card.objects.filter(text__startswith="Late").exists()


def test_card_mutations_require_csrf(alice, cycle):
    card = create_card(cycle, alice)
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(alice)

    create_response = csrf_client.post(
        reverse("cycles:card-create", args=(cycle.pk, Card.Category.START)),
        {"text": "No token"},
    )
    edit_response = csrf_client.post(
        reverse("cycles:card-edit", args=(card.pk,)), {"text": "No token"}
    )
    delete_response = csrf_client.post(reverse("cycles:card-delete", args=(card.pk,)))

    assert create_response.status_code == 403
    assert edit_response.status_code == 403
    assert delete_response.status_code == 403
