from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


def demo_swap(request: HttpRequest) -> HttpResponse:
    return render(request, "partials/demo_swap.html")


urlpatterns = [
    path("", home, name="home"),
    path("demo/swap/", demo_swap, name="demo-swap"),
    path("admin/", admin.site.urls),
]
