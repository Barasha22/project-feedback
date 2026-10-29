from django.urls import path

from . import views

app_name = "cycles"

urlpatterns = [
    path(
        "projects/<int:project_id>/cycles/new/",
        views.cycle_create,
        name="create",
    ),
    path("cycles/<int:cycle_id>/close/", views.cycle_close, name="close"),
]
