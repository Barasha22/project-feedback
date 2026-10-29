from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:project_id>/", views.project_detail, name="detail"),
    path(
        "<int:project_id>/rotate-join-token/",
        views.rotate_join_token,
        name="rotate-join-token",
    ),
]
