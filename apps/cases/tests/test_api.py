import pytest
import requests
from django.db import DatabaseError
from rest_framework import status

from apps.cases.services.airport_service import AirportProviderUnavailableError, AirportRecord


@pytest.mark.django_db
def test_public_case_creation_returns_201(api_client, multipart_case_payload, monkeypatch):
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=1871,
        ),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "NEW"
    assert response.data["colleague"] is None
    assert response.data["disruption_details"]["disruption_type"] == "DELAY"
    assert response.data["disruption_details"]["airline_motive_details"] == "Technical problem"
    assert str(response.data["orthodromic_distance_km"]) == "1871.00"
    assert response.data["compensation_amount_eur"] == 400
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
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=1200,
        ),
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
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=1200,
        ),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "gdpr_consent" in response.data


@pytest.mark.django_db
def test_case_creation_rejects_missing_disruption_description(api_client, multipart_case_payload, monkeypatch):
    multipart_case_payload["disruption_details"] = '{"disruption_type": "DELAY", "incident_description": ""}'
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=1200,
        ),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "disruption_details" in response.data


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


@pytest.mark.django_db
def test_compensation_preview_returns_distance_and_amount(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=3499.99,
        ),
    )

    response = api_client.post(
        "/api/cases/compensation-preview/",
        data={"departure_airport_code": "otp", "arrival_airport_code": "mad"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["departure_airport_code"] == "OTP"
    assert response.data["arrival_airport_code"] == "MAD"
    assert response.data["orthodromic_distance_km"] == "3499.99"
    assert response.data["compensation_amount_eur"] == 400


@pytest.mark.django_db
def test_case_creation_returns_json_error_when_database_save_fails(api_client, multipart_case_payload, monkeypatch):
    monkeypatch.setattr(
        "apps.cases.services.case_service.Disruption.objects.create",
        lambda **kwargs: (_ for _ in ()).throw(DatabaseError("database write failed")),
    )
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.ensure_airport_exists",
        lambda self, code: AirportRecord(code=code, name=code, city=None, country=None),
    )
    monkeypatch.setattr(
        "apps.cases.services.airport_service.AirportService.calculate_distance",
        lambda self, from_airport_code, to_airport_code: __import__(
            "apps.cases.services.airport_service", fromlist=["AirportDistanceResult"]
        ).AirportDistanceResult(
            from_airport_code=from_airport_code,
            to_airport_code=to_airport_code,
            kilometers=1200,
        ),
    )

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data["detail"] == "The case could not be saved. Please try again."
