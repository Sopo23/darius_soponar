from __future__ import annotations

from collections.abc import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cases.constants import (
    COMPENSATION_AMOUNT_LONG_HAUL_EUR,
    COMPENSATION_AMOUNT_MEDIUM_HAUL_EUR,
    COMPENSATION_AMOUNT_SHORT_HAUL_EUR,
    COMPENSATION_THRESHOLD_MEDIUM_HAUL_KM,
    COMPENSATION_THRESHOLD_SHORT_HAUL_KM,
    DocumentType,
    MAX_CONNECTING_FLIGHTS,
    MAX_TOTAL_FLIGHTS,
)
from apps.cases.models import Case, CaseDocument, FlightSegment


class CaseCreationService:
    def __init__(self, *, account_service, airport_service) -> None:
        self.account_service = account_service
        self.airport_service = airport_service

    @transaction.atomic
    def create_case(self, *, authenticated_user, validated_data: dict) -> Case:
        validated_data = {
            **validated_data,
            "flight_segments": [*validated_data["flight_segments"]],
            "documents": [*validated_data["documents"]],
            "passenger": {**validated_data["passenger"]},
            "disruption_details": {**validated_data["disruption_details"]},
        }
        flight_segments = list(validated_data.pop("flight_segments"))
        documents = list(validated_data.pop("documents"))
        passenger = validated_data.pop("passenger")
        disruption_details = validated_data.pop("disruption_details")

        self._validate_flight_segments(flight_segments)
        self._validate_documents(documents)
        self._validate_gdpr_consent(validated_data.get("gdpr_consent"))
        self._validate_disruption_details(disruption_details)
        self._validate_airports(flight_segments)
        distance_result = self._calculate_distance(flight_segments)
        compensation_amount = self._calculate_compensation_amount(distance_result.kilometers)

        owner = self._resolve_owner(
            authenticated_user=authenticated_user,
            passenger_email=passenger["email"],
            first_name=passenger["first_name"],
            last_name=passenger["last_name"],
        )

        case = Case.objects.create(
            owner=owner,
            contact_email=passenger["email"],
            gdpr_consent=True,
            gdpr_consented_at=timezone.now(),
            disruption_type=disruption_details.get("disruption_type"),
            cancellation_notice_timing=disruption_details.get("cancellation_notice_timing") or "",
            delay_arrival_timing=disruption_details.get("delay_arrival_timing") or "",
            denied_boarding_voluntary=disruption_details.get("denied_boarding_voluntary") or "",
            denied_boarding_reason=disruption_details.get("denied_boarding_reason") or "",
            airline_motive_known=disruption_details.get("airline_motive_known") or "",
            airline_motive_details=disruption_details.get("airline_motive_details") or "",
            incident_description=disruption_details.get("incident_description", "").strip(),
            orthodromic_distance_km=distance_result.kilometers,
            compensation_amount_eur=compensation_amount,
        )

        self._create_flight_segments(case=case, flight_segments=flight_segments)
        self._create_documents(case=case, documents=documents)

        return case

    def _validate_flight_segments(self, flight_segments: list[dict]) -> None:
        if not flight_segments:
            raise ValidationError({"flight_segments": ["At least one flight is required."]})

        if len(flight_segments) > MAX_TOTAL_FLIGHTS:
            raise ValidationError(
                {"flight_segments": [f"A passenger may add up to {MAX_CONNECTING_FLIGHTS} connecting flights."]}
            )

        problem_flights = sum(1 for segment in flight_segments if segment["is_problem_flight"])
        if problem_flights != 1:
            raise ValidationError({"flight_segments": ["Exactly one problem flight must be selected."]})

    def _validate_documents(self, documents: list[dict]) -> None:
        if len(documents) != 2:
            raise ValidationError(
                {"documents": ["Exactly two documents are required: boarding pass and ID/passport."]}
            )

        document_types = {document["document_type"] for document in documents}
        required_document_types = {DocumentType.BOARDING_PASS, DocumentType.ID_OR_PASSPORT}
        if document_types != required_document_types:
            raise ValidationError(
                {"documents": ["Both boarding pass and ID/passport documents are required."]}
            )

    def _validate_gdpr_consent(self, gdpr_consent: bool) -> None:
        if gdpr_consent is not True:
            raise ValidationError({"gdpr_consent": ["GDPR consent is required."]})

    def _validate_disruption_details(self, disruption_details: dict) -> None:
        disruption_type = disruption_details.get("disruption_type")
        incident_description = (disruption_details.get("incident_description") or "").strip()

        errors = []
        if not disruption_type:
            errors.append("Disruption type is required.")
        if not incident_description:
            errors.append("Incident description is required.")
        if errors:
            raise ValidationError({"disruption_details": errors})

    def _validate_airports(self, flight_segments: Iterable[dict]) -> None:
        for flight_segment in flight_segments:
            self.airport_service.ensure_airport_exists(flight_segment["departure_airport_code"])
            self.airport_service.ensure_airport_exists(flight_segment["arrival_airport_code"])

    def _calculate_distance(self, flight_segments: list[dict]):
        ordered_segments = sorted(flight_segments, key=lambda item: item["sequence_number"])
        return self.airport_service.calculate_distance(
            from_airport_code=ordered_segments[0]["departure_airport_code"],
            to_airport_code=ordered_segments[-1]["arrival_airport_code"],
        )

    def _calculate_compensation_amount(self, distance_km):
        if distance_km < COMPENSATION_THRESHOLD_SHORT_HAUL_KM:
            return COMPENSATION_AMOUNT_SHORT_HAUL_EUR
        if distance_km <= COMPENSATION_THRESHOLD_MEDIUM_HAUL_KM:
            return COMPENSATION_AMOUNT_MEDIUM_HAUL_EUR
        return COMPENSATION_AMOUNT_LONG_HAUL_EUR

    def _resolve_owner(self, *, authenticated_user, passenger_email: str, first_name: str, last_name: str):
        if authenticated_user is not None:
            if authenticated_user.email.lower() != passenger_email.lower():
                raise ValidationError(
                    {"passenger": {"email": ["Authenticated passengers must use their own email address."]}}
                )
            return authenticated_user

        result = self.account_service.resolve_or_create(
            email=passenger_email,
            first_name=first_name,
            last_name=last_name,
        )
        return result.user

    def _create_flight_segments(self, *, case: Case, flight_segments: list[dict]) -> None:
        FlightSegment.objects.bulk_create(
            FlightSegment(case=case, **flight_segment)
            for flight_segment in flight_segments
        )

    def _create_documents(self, *, case: Case, documents: list[dict]) -> None:
        for document in documents:
            CaseDocument.objects.create(
                case=case,
                document_type=document["document_type"],
                file=document["file"],
                original_filename=document["file"].name,
                content_type=getattr(document["file"], "content_type", "application/octet-stream"),
                file_size=document["file"].size,
            )
