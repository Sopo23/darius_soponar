import pytest
import requests
from rest_framework import status

from apps.cases.services.airport_service import AirportProviderUnavailableError, AirportRecord


@pytest.mark.django_db
def test_public_case_creation_returns_201(api_client, multipart_case_payload, monkeypatch):
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "NEW"
    assert len(response.data["flight_segments"]) == 1
    assert len(response.data["documents"]) == 2


@pytest.mark.django_db
def test_authenticated_case_creation_reuses_logged_in_user(api_client, multipart_case_payload, monkeypatch, user):
    multipart_case_payload["passenger"] = '{"email": "registered@example.com", "first_name": "Registered", "last_name": "Passenger"}'
    api_client.force_authenticate(user=user)
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["contact_email"] == user.email


@pytest.mark.django_db
def test_airport_search_returns_normalized_payload(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.search",
        lambda self, query: [AirportRecord(code="OTP", name="Henri Coanda", city="Bucharest", country="Romania")],
    )

    response = api_client.get("/api/airports/", {"search": "ot"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data == [
        {
            "code": "OTP",
            "name": "Henri Coanda",
            "city": "Bucharest",
            "country": "Romania",
        }
    ]


@pytest.mark.django_db
def test_airport_search_returns_503_when_provider_fails(api_client, monkeypatch):
    def raise_lookup_error(self, query):
        raise AirportProviderUnavailableError("Airport provider unavailable")

    monkeypatch.setattr("apps.cases.services.airport_service.AirportService.search", raise_lookup_error)

    response = api_client.get("/api/airports/", {"search": "otp"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_case_creation_rejects_missing_gdpr_consent(api_client, multipart_case_payload, monkeypatch):
    multipart_case_payload["gdpr_consent"] = "false"
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "gdpr_consent" in response.data


@pytest.mark.django_db
def test_case_creation_returns_503_when_airport_provider_ssl_fails(api_client, multipart_case_payload, monkeypatch):
    def raise_ssl_error(self, url, timeout, verify):
        raise requests.exceptions.SSLError("certificate verify failed")

    monkeypatch.setattr(
        "requests.sessions.Session.get",
        raise_ssl_error,
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "SSL verification failed" in response.data["detail"]
