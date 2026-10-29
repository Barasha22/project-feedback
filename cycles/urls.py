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
    path(
        "cycles/<int:cycle_id>/feedback/",
        views.feedback_cards,
        name="feedback-cards",
    ),
    path(
        "cycles/<int:cycle_id>/cards/<str:category>/create/",
        views.card_create,
        name="card-create",
    ),
    path("cards/<int:card_id>/edit/", views.card_edit, name="card-edit"),
    path("cards/<int:card_id>/delete/", views.card_delete, name="card-delete"),
]
