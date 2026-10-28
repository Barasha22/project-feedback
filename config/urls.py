from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path


def home(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Project Feedback")


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
]

