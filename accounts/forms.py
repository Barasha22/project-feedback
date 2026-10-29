from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import CharField


class SignupForm(UserCreationForm):
    display_name = CharField(max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "display_name")

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["display_name"]
        if commit:
            user.save()
        return user
