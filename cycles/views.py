from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from projects.models import Membership, Project

from .forms import FeedbackCycleForm
from .models import FeedbackCycle


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
