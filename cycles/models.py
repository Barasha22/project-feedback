from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, Q

from projects.models import Project


class FeedbackCycle(models.Model):
    class Status(models.TextChoices):
        COLLECTING = "COLLECTING", "Collecting"
        CLOSED = "CLOSED", "Closed"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="feedback_cycles"
    )
    week_start = models.DateField()
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    facilitator = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="facilitated_cycles"
    )
    status = models.CharField(max_length=20, choices=Status, default=Status.COLLECTING)

    class Meta:
        ordering = ("-week_start", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("project",),
                condition=Q(status="COLLECTING"),
                name="one_collecting_cycle_per_project",
            ),
            models.CheckConstraint(
                condition=Q(closes_at__gt=F("opens_at")),
                name="cycle_closes_after_opening",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.name} · {self.week_start}"
