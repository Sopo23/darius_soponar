from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.cases.models import Case


@pytest.mark.django_db
def test_anonymous_submission_creates_user_and_case(case_creation_service, valid_case_payload):
    case = case_creation_service.create_case(
        authenticated_user=None,
        validated_data=valid_case_payload,
    )

    assert case.owner.email == valid_case_payload["passenger"]["email"]
    assert case.status == "NEW"
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
