import pytest
from django.utils import timezone

from apps.cases.constants import CaseStatus, DocumentType
from apps.cases.models import Case, CaseDocument, Disruption, FlightSegment


@pytest.mark.django_db
def test_case_defaults_to_new_status(user):
    case = Case.objects.create(
        owner=user,
        contact_email="traveler@example.com",
        gdpr_consent=True,
        gdpr_consented_at=timezone.now(),
    )

    assert case.status == CaseStatus.NEW
    assert case.colleague is None


@pytest.mark.django_db
def test_case_document_persists_metadata(user):
    case = Case.objects.create(
        owner=user,
        contact_email="traveler@example.com",
        gdpr_consent=True,
        gdpr_consented_at=timezone.now(),
    )

    document = CaseDocument.objects.create(
        case=case,
        document_type=DocumentType.BOARDING_PASS,
        file="case_documents/2026/07/23/boarding-pass.pdf",
        original_filename="boarding-pass.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    assert document.document_type == DocumentType.BOARDING_PASS
    assert document.original_filename == "boarding-pass.pdf"


@pytest.mark.django_db
def test_case_tracks_related_flight_segments(user):
    case = Case.objects.create(
        owner=user,
        contact_email="traveler@example.com",
        gdpr_consent=True,
        gdpr_consented_at=timezone.now(),
    )

    FlightSegment.objects.create(
        case=case,
        sequence_number=1,
        departure_airport_code="OTP",
        arrival_airport_code="CDG",
        flight_number="AF1089",
        flight_date=timezone.now().date(),
        airline="Air France",
        is_problem_flight=True,
    )

    assert case.flight_segments.count() == 1


@pytest.mark.django_db
def test_case_tracks_related_disruption(user):
    case = Case.objects.create(
        owner=user,
        contact_email="traveler@example.com",
        gdpr_consent=True,
        gdpr_consented_at=timezone.now(),
    )

    disruption = Disruption.objects.create(
        case=case,
        disruption_type="DELAY",
        incident_description="The flight arrived four hours late.",
    )

    assert case.disruption == disruption
