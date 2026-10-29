from django.contrib.auth.models import User
from django.forms import CheckboxInput, DateInput, DateTimeInput, ModelForm, Textarea

from projects.models import Project

from .models import Card, FeedbackCycle


class FeedbackCycleForm(ModelForm):
    class Meta:
        model = FeedbackCycle
        fields = ("week_start", "opens_at", "closes_at", "facilitator")
        widgets = {
            "week_start": DateInput(attrs={"type": "date"}),
            "opens_at": DateTimeInput(attrs={"type": "datetime-local"}),
            "closes_at": DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, project: Project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facilitator"].queryset = User.objects.filter(
            project_memberships__project=project
        ).order_by("username")


class CardForm(ModelForm):
    class Meta:
        model = Card
        fields = ("text", "is_anonymous")
        widgets = {
            "text": Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 500,
                    "placeholder": "Add a short feedback card…",
                }
            ),
            "is_anonymous": CheckboxInput(),
        }
