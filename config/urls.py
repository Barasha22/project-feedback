from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import include, path

from projects.views import join_project


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


def demo_swap(request: HttpRequest) -> HttpResponse:
    return render(request, "partials/demo_swap.html")


urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("demo/swap/", demo_swap, name="demo-swap"),
    path("projects/", include("projects.urls")),
    path("join/<uuid:token>/", join_project, name="join-project"),
    path("admin/", admin.site.urls),
]
