from django.urls import path

from apps.cases.views import AirportSearchView, CaseCreateView


urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("airports/", AirportSearchView.as_view(), name="airport-search"),
]
