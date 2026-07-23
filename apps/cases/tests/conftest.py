import json
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.cases.constants import DocumentType
from apps.cases.services.account_service import PassengerAccountService
from apps.cases.services.airport_service import AirportRecord
from apps.cases.services.case_service import CaseCreationService


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="registered@example.com",
        password="password123",
        first_name="Registered",
        last_name="Passenger",
    )


@pytest.fixture
def uploaded_documents():
    return [
        {
            "document_type": DocumentType.BOARDING_PASS,
            "file": SimpleUploadedFile(
                "boarding-pass.pdf",
                b"%PDF-1.4 boarding pass",
                content_type="application/pdf",
            ),
        },
        {
            "document_type": DocumentType.ID_OR_PASSPORT,
            "file": SimpleUploadedFile(
                "passport.jpg",
                b"jpeg-binary",
                content_type="image/jpeg",
            ),
        },
    ]


@pytest.fixture
def valid_case_payload(uploaded_documents):
    return {
        "passenger": {
            "email": "traveler@example.com",
            "first_name": "Casey",
            "last_name": "Traveler",
        },
        "gdpr_consent": True,
        "flight_segments": [
            {
                "sequence_number": 1,
                "departure_airport_code": "OTP",
                "arrival_airport_code": "CDG",
                "flight_number": "AF1089",
                "flight_date": date(2026, 7, 23),
                "airline": "Air France",
                "is_problem_flight": True,
            }
        ],
        "documents": uploaded_documents,
    }


@pytest.fixture
def multipart_case_payload():
    return {
        "passenger": json.dumps(
            {
                "email": "traveler@example.com",
                "first_name": "Casey",
                "last_name": "Traveler",
            }
        ),
        "gdpr_consent": "true",
        "flight_segments": json.dumps(
            [
                {
                    "sequence_number": 1,
                    "departure_airport_code": "OTP",
                    "arrival_airport_code": "CDG",
                    "flight_number": "AF1089",
                    "flight_date": "2026-07-23",
                    "airline": "Air France",
                    "is_problem_flight": True,
                }
            ]
        ),
        "document_types": [DocumentType.BOARDING_PASS, DocumentType.ID_OR_PASSPORT],
        "document_files": [
            SimpleUploadedFile("boarding-pass.pdf", b"%PDF-1.4 boarding pass", content_type="application/pdf"),
            SimpleUploadedFile("passport.jpg", b"jpeg-binary", content_type="image/jpeg"),
        ],
    }


class StubAirportService:
    def search(self, query):
        return [AirportRecord(code="OTP", name="Henri Coanda", city="Bucharest", country="Romania")]

    def ensure_airport_exists(self, airport_code):
        return AirportRecord(code=airport_code.upper(), name=airport_code.upper(), city=None, country=None)


@pytest.fixture
def case_creation_service():
    return CaseCreationService(
        account_service=PassengerAccountService(),
        airport_service=StubAirportService(),
    )
