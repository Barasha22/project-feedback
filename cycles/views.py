from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from projects.models import Membership, Project

from .forms import CardForm, FeedbackCycleForm
from .models import Card, FeedbackCycle


def _member_cycle(request: HttpRequest, cycle_id: int) -> FeedbackCycle:
    return get_object_or_404(
        FeedbackCycle.objects.select_related("project").filter(
            project__memberships__user=request.user
        ),
        pk=cycle_id,
    )


def _own_cards(cycle: FeedbackCycle, user) -> list[Card]:
    return list(Card.objects.filter(cycle=cycle, author=user))


def _column_context(cycle: FeedbackCycle, user, category: str, form=None) -> dict:
    return {
        "cycle": cycle,
        "category": category,
        "category_label": Card.Category(category).label,
        "cards": [
            card for card in _own_cards(cycle, user) if card.category == category
        ],
        "form": form or CardForm(),
        "can_edit": cycle.status == FeedbackCycle.Status.COLLECTING,
    }


def _page_context(cycle: FeedbackCycle, user, forms=None) -> dict:
    forms = forms or {}
    return {
        "cycle": cycle,
        "columns": [
            _column_context(cycle, user, category, forms.get(category))
            for category in Card.Category.values
        ],
    }


def _is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def _render_column(
    request: HttpRequest, cycle: FeedbackCycle, category: str, form=None
) -> HttpResponse:
    return render(
        request,
        "cycles/partials/card_column.html",
        _column_context(cycle, request.user, category, form),
    )


@login_required
@require_http_methods(["GET", "POST"])
def cycle_create(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(
        Project,
        pk=project_id,
        memberships__user=request.user,
        memberships__role=Membership.Role.FACILITATOR,
    )
    if request.method == "POST":
        form = FeedbackCycleForm(request.POST, project=project)
        if form.is_valid():
            cycle = form.save(commit=False)
            cycle.project = project
            try:
                with transaction.atomic():
                    cycle.save()
            except IntegrityError:
                form.add_error(
                    None, "This project already has a cycle collecting feedback."
                )
            else:
                messages.success(request, "Feedback cycle opened.")
                return redirect("projects:detail", project_id=project.pk)
    else:
        form = FeedbackCycleForm(project=project)
    return render(
        request,
        "cycles/cycle_form.html",
        {"form": form, "project": project},
    )


@login_required
@require_POST
def cycle_close(request: HttpRequest, cycle_id: int) -> HttpResponse:
    cycle = get_object_or_404(
        FeedbackCycle.objects.select_related("project"),
        pk=cycle_id,
        facilitator=request.user,
    )
    if cycle.status == FeedbackCycle.Status.COLLECTING:
        cycle.status = FeedbackCycle.Status.CLOSED
        cycle.save(update_fields=("status",))
        messages.success(request, "Feedback cycle closed.")
    else:
        messages.info(request, "Feedback cycle is already closed.")
    return redirect("projects:detail", project_id=cycle.project_id)


@login_required
def feedback_cards(request: HttpRequest, cycle_id: int) -> HttpResponse:
    cycle = _member_cycle(request, cycle_id)
    return render(
        request,
        "cycles/feedback_cards.html",
        _page_context(cycle, request.user),
    )


@login_required
@require_POST
def card_create(request: HttpRequest, cycle_id: int, category: str) -> HttpResponse:
    cycle = _member_cycle(request, cycle_id)
    if category not in Card.Category.values:
        raise Http404
    if cycle.status != FeedbackCycle.Status.COLLECTING:
        return HttpResponse("Feedback collection is closed.", status=409)

    form = CardForm(request.POST)
    if form.is_valid():
        card = form.save(commit=False)
        card.cycle = cycle
        card.category = category
        card.author = request.user
        last_position = Card.objects.filter(
            cycle=cycle, author=request.user, category=category
        ).aggregate(last=Max("position"))["last"]
        card.position = (last_position if last_position is not None else -1) + 1
        card.save()
        if _is_htmx(request):
            return _render_column(request, cycle, category)
        return redirect("cycles:feedback-cards", cycle_id=cycle.pk)

    if _is_htmx(request):
        return _render_column(request, cycle, category, form)
    return render(
        request,
        "cycles/feedback_cards.html",
        _page_context(cycle, request.user, {category: form}),
        status=400,
    )


@login_required
@require_http_methods(["GET", "POST"])
def card_edit(request: HttpRequest, card_id: int) -> HttpResponse:
    card = get_object_or_404(
        Card.objects.select_related("cycle__project"),
        pk=card_id,
        author=request.user,
        cycle__project__memberships__user=request.user,
    )
    if card.cycle.status != FeedbackCycle.Status.COLLECTING:
        return HttpResponse("Feedback collection is closed.", status=409)

    if request.method == "POST":
        form = CardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            if _is_htmx(request):
                return _render_column(request, card.cycle, card.category)
            return redirect("cycles:feedback-cards", cycle_id=card.cycle_id)
    else:
        form = CardForm(instance=card)

    template = (
        "cycles/partials/card_edit_form.html"
        if _is_htmx(request)
        else "cycles/card_edit.html"
    )
    return render(request, template, {"card": card, "form": form})


@login_required
@require_POST
def card_delete(request: HttpRequest, card_id: int) -> HttpResponse:
    card = get_object_or_404(
        Card.objects.select_related("cycle__project"),
        pk=card_id,
        author=request.user,
        cycle__project__memberships__user=request.user,
    )
    if card.cycle.status != FeedbackCycle.Status.COLLECTING:
        return HttpResponse("Feedback collection is closed.", status=409)
    cycle = card.cycle
    category = card.category
    card.delete()
    if _is_htmx(request):
        return _render_column(request, cycle, category)
    return redirect("cycles:feedback-cards", cycle_id=cycle.pk)
