import uuid

from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="owned_projects"
    )
    join_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name", "pk")

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Member"
        FACILITATOR = "FACILITATOR", "Facilitator"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role = models.CharField(max_length=20, choices=Role, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "user"), name="unique_project_membership"
            )
        ]
        ordering = ("joined_at", "pk")

    def __str__(self) -> str:
        return f"{self.user.username} in {self.project.name}"
