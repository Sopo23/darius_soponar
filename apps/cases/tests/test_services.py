from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cases.models import Case
from apps.cases.services.airport_service import AirportDistanceResult, AirportService


@pytest.mark.django_db
def test_anonymous_submission_creates_user_and_case(case_creation_service, valid_case_payload):
    case = case_creation_service.create_case(
        authenticated_user=None,
        validated_data=valid_case_payload,
    )

    assert case.owner.email == valid_case_payload["passenger"]["email"]
    assert case.status == "NEW"
    assert case.disruption_type == "DELAY"
    assert case.incident_description == "The aircraft arrived more than three hours late at the final destination."
    assert case.orthodromic_distance_km == Decimal("1871.00")
    assert case.compensation_amount_eur == 400
    assert case.flight_segments.count() == 1
    assert case.documents.count() == 2


@pytest.mark.django_db
def test_authenticated_submission_reuses_existing_user(case_creation_service, valid_case_payload, user):
    valid_case_payload["passenger"]["email"] = user.email
    valid_case_payload["passenger"]["first_name"] = user.first_name
    valid_case_payload["passenger"]["last_name"] = user.last_name

    case = case_creation_service.create_case(
        authenticated_user=user,
        validated_data=valid_case_payload,
    )

    assert case.owner == user
    assert Case.objects.filter(owner=user).count() == 1


@pytest.mark.django_db
def test_multiple_problem_flights_are_rejected(case_creation_service, valid_case_payload):
    valid_case_payload["flight_segments"].append(
        {
            "sequence_number": 2,
            "departure_airport_code": "CDG",
            "arrival_airport_code": "AMS",
            "flight_number": "KL1402",
            "flight_date": date(2026, 7, 24),
            "airline": "KLM",
            "is_problem_flight": True,
        }
    )

    with pytest.raises(ValidationError, match="Exactly one problem flight"):
        case_creation_service.create_case(authenticated_user=None, validated_data=valid_case_payload)


@pytest.mark.django_db
def test_more_than_four_connections_are_rejected(case_creation_service, valid_case_payload):
    for index in range(2, 7):
        valid_case_payload["flight_segments"].append(
            {
                "sequence_number": index,
                "departure_airport_code": "AAA",
                "arrival_airport_code": "BBB",
                "flight_number": f"ZZ{index}",
                "flight_date": date(2026, 7, 24),
                "airline": "Test Air",
                "is_problem_flight": False,
            }
        )

    with pytest.raises(ValidationError, match="up to 4 connecting flights"):
        case_creation_service.create_case(authenticated_user=None, validated_data=valid_case_payload)


@pytest.mark.django_db
def test_missing_gdpr_consent_is_rejected(case_creation_service, valid_case_payload):
    valid_case_payload["gdpr_consent"] = False

    with pytest.raises(ValidationError, match="GDPR consent is required"):
        case_creation_service.create_case(authenticated_user=None, validated_data=valid_case_payload)


@pytest.mark.django_db
def test_missing_incident_description_is_rejected(case_creation_service, valid_case_payload):
    valid_case_payload["disruption_details"]["incident_description"] = "   "

    with pytest.raises(ValidationError, match="Incident description is required"):
        case_creation_service.create_case(authenticated_user=None, validated_data=valid_case_payload)


@pytest.mark.django_db
def test_distance_uses_first_departure_and_final_arrival(valid_case_payload):
    class DistanceAwareAirportService:
        def __init__(self):
            self.distance_calls = []

        def ensure_airport_exists(self, airport_code):
            return None

        def calculate_distance(self, *, from_airport_code, to_airport_code):
            self.distance_calls.append((from_airport_code, to_airport_code))
            return AirportDistanceResult(
                from_airport_code=from_airport_code,
                to_airport_code=to_airport_code,
                kilometers=Decimal("3600.00"),
            )

    airport_service = DistanceAwareAirportService()
    service = case_creation_service = __import__(
        "apps.cases.services.case_service", fromlist=["CaseCreationService"]
    ).CaseCreationService(
        account_service=__import__(
            "apps.cases.services.account_service", fromlist=["PassengerAccountService"]
        ).PassengerAccountService(),
        airport_service=airport_service,
    )

    valid_case_payload["flight_segments"] = [
        {
            "sequence_number": 1,
            "departure_airport_code": "OTP",
            "arrival_airport_code": "CDG",
            "flight_number": "AF1089",
            "flight_date": date(2026, 7, 23),
            "airline": "Air France",
            "is_problem_flight": True,
        },
        {
            "sequence_number": 2,
            "departure_airport_code": "CDG",
            "arrival_airport_code": "MAD",
            "flight_number": "AF1401",
            "flight_date": date(2026, 7, 23),
            "airline": "Air France",
            "is_problem_flight": False,
        },
    ]

    case = service.create_case(authenticated_user=None, validated_data=valid_case_payload)

    assert airport_service.distance_calls == [("OTP", "MAD")]
    assert case.compensation_amount_eur == 600


def test_airport_search_uses_local_index(monkeypatch):
    monkeypatch.setattr(
        'apps.cases.services.airport_service._load_airport_records',
        lambda: (
            __import__('apps.cases.services.airport_service', fromlist=['AirportRecord']).AirportRecord(
                code='GKA',
                name='Goroka Airport',
                city='Goroka',
                country='Papua New Guinea',
            ),
            __import__('apps.cases.services.airport_service', fromlist=['AirportRecord']).AirportRecord(
                code='OTP',
                name='Henri Coanda International Airport',
                city='Bucharest',
                country='Romania',
            ),
        ),
    )

    service = AirportService(base_url='https://example.test')

    results = service.search('bucharest')

    assert [airport.code for airport in results] == ['OTP']
