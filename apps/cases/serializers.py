from __future__ import annotations

import json
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.cases.constants import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    DisruptionType,
    DocumentType,
    MAX_DOCUMENT_SIZE_BYTES,
)
from apps.cases.models import Case


class PassengerSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)


class FlightSegmentSerializer(serializers.Serializer):
    sequence_number = serializers.IntegerField(min_value=1)
    departure_airport_code = serializers.CharField(max_length=3, min_length=3)
    arrival_airport_code = serializers.CharField(max_length=3, min_length=3)
    flight_number = serializers.CharField(max_length=20)
    flight_date = serializers.DateField()
    airline = serializers.CharField(max_length=120)
    is_problem_flight = serializers.BooleanField()

    def validate_departure_airport_code(self, value: str) -> str:
        return value.upper()

    def validate_arrival_airport_code(self, value: str) -> str:
        return value.upper()


class CaseDocumentSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(choices=DocumentType.choices)
    file = serializers.FileField()

    def validate_file(self, value):
        extension = Path(value.name).suffix.lower()
        if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise serializers.ValidationError("Only PDF, JPG, and JPEG files are allowed.")
        if value.size > MAX_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError("Each uploaded file must be 5 MB or smaller.")
        return value


class DisruptionDetailsSerializer(serializers.Serializer):
    disruption_type = serializers.ChoiceField(choices=DisruptionType.choices)
    cancellation_notice_timing = serializers.CharField(max_length=32, required=False, allow_blank=True)
    delay_arrival_timing = serializers.CharField(max_length=32, required=False, allow_blank=True)
    denied_boarding_voluntary = serializers.CharField(max_length=16, required=False, allow_blank=True)
    denied_boarding_reason = serializers.CharField(max_length=64, required=False, allow_blank=True)
    airline_motive_known = serializers.CharField(max_length=16, required=False, allow_blank=True)
    airline_motive_details = serializers.CharField(max_length=64, required=False, allow_blank=True)
    incident_description = serializers.CharField(max_length=4000, allow_blank=True)


class CaseCreateSerializer(serializers.Serializer):
    passenger = PassengerSerializer()
    gdpr_consent = serializers.BooleanField()
    flight_segments = FlightSegmentSerializer(many=True)
    documents = CaseDocumentSerializer(many=True)
    disruption_details = DisruptionDetailsSerializer()

    def to_internal_value(self, data):
        normalized_data = self._normalize_multipart_payload(data)
        return super().to_internal_value(normalized_data)

    def create(self, validated_data):
        raise NotImplementedError("Case creation is handled by the service layer.")

    def update(self, instance: Case, validated_data):
        raise NotImplementedError("Case updates are not implemented for CASE_01.")

    def _normalize_multipart_payload(self, data):
        if not hasattr(data, "getlist"):
            return data

        normalized = {
            "gdpr_consent": data.get("gdpr_consent"),
        }

        for nested_field in ("passenger", "flight_segments", "disruption_details"):
            raw_value = data.get(nested_field)
            if isinstance(raw_value, str):
                normalized[nested_field] = self._parse_json_string(field_name=nested_field, raw_value=raw_value)

        document_types = data.getlist("document_types")
        document_files = data.getlist("document_files")
        if document_types or document_files:
            normalized["documents"] = [
                {"document_type": document_type, "file": document_file}
                for document_type, document_file in zip(document_types, document_files, strict=False)
            ]

        return normalized

    def _parse_json_string(self, *, field_name: str, raw_value: str):
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError({field_name: ["Must be valid JSON."]}) from exc

    def validate(self, attrs):
        flights = attrs.get("flight_segments", [])
        if flights != sorted(flights, key=lambda item: item["sequence_number"]):
            raise serializers.ValidationError(
                {"flight_segments": ["Flight segments must be ordered by sequence number."]}
            )
        return attrs


class AirportQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=100)


class AirportResultSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    city = serializers.CharField(allow_null=True)
    country = serializers.CharField(allow_null=True)


class CompensationPreviewSerializer(serializers.Serializer):
    departure_airport_code = serializers.CharField(max_length=3, min_length=3)
    arrival_airport_code = serializers.CharField(max_length=3, min_length=3)

    def validate_departure_airport_code(self, value: str) -> str:
        return value.upper()

    def validate_arrival_airport_code(self, value: str) -> str:
        return value.upper()
