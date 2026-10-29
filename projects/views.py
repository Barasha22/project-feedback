import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ProjectForm
from .models import Membership, Project


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    projects = Project.objects.filter(memberships__user=request.user).distinct()
    return render(request, "projects/project_list.html", {"projects": projects})


@login_required
@require_http_methods(["GET", "POST"])
def project_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                project = form.save(commit=False)
                project.owner = request.user
                project.save()
                Membership.objects.create(
                    project=project,
                    user=request.user,
                    role=Membership.Role.FACILITATOR,
                )
            messages.success(request, "Project created.")
            return redirect("projects:detail", project_id=project.pk)
    else:
        form = ProjectForm()
    return render(request, "projects/project_form.html", {"form": form})


@login_required
def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(
        Project.objects.prefetch_related(
            "memberships__user", "feedback_cycles__facilitator"
        ).filter(memberships__user=request.user),
        pk=project_id,
    )
    can_create_cycle = project.memberships.filter(
        user=request.user, role=Membership.Role.FACILITATOR
    ).exists()
    return render(
        request,
        "projects/project_detail.html",
        {"project": project, "can_create_cycle": can_create_cycle},
    )


@login_required
@require_http_methods(["GET", "POST"])
def join_project(request: HttpRequest, token: uuid.UUID) -> HttpResponse:
    project = get_object_or_404(Project, join_token=token)
    if request.method == "POST":
        _membership, created = Membership.objects.get_or_create(
            project=project,
            user=request.user,
            defaults={"role": Membership.Role.MEMBER},
        )
        if created:
            messages.success(request, f"You joined {project.name}.")
        else:
            messages.info(request, f"You are already a member of {project.name}.")
        return redirect("projects:detail", project_id=project.pk)
    return render(request, "projects/join_confirm.html", {"project": project})


@login_required
@require_POST
def rotate_join_token(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(Project, pk=project_id, owner=request.user)
    project.join_token = uuid.uuid4()
    project.save(update_fields=("join_token",))
    messages.success(request, "Join link rotated. The previous link no longer works.")
    return redirect("projects:detail", project_id=project.pk)
