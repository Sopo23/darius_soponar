from django.urls import path

from apps.cases.views import AirportSearchView, CaseCreateView, CompensationPreviewView


urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("cases/compensation-preview/", CompensationPreviewView.as_view(), name="case-compensation-preview"),
    path("airports/", AirportSearchView.as_view(), name="airport-search"),
]
