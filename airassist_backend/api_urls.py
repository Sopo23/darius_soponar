"""API URL configuration for airassist_backend."""

from django.urls import include, path


urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("", include("apps.cases.urls")),
]
