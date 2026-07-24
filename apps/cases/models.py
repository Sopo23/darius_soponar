from django.conf import settings
from django.db import models

from .constants import CaseStatus, DisruptionType, DocumentType


class Case(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cases")
    colleague = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=CaseStatus.choices, default=CaseStatus.NEW)
    contact_email = models.EmailField()
    gdpr_consent = models.BooleanField()
    gdpr_consented_at = models.DateTimeField()
    disruption_type = models.CharField(max_length=32, choices=DisruptionType.choices, null=True, blank=True)
    cancellation_notice_timing = models.CharField(max_length=32, null=True, blank=True)
    delay_arrival_timing = models.CharField(max_length=32, null=True, blank=True)
    denied_boarding_voluntary = models.CharField(max_length=16, null=True, blank=True)
    denied_boarding_reason = models.CharField(max_length=64, null=True, blank=True)
    airline_motive_known = models.CharField(max_length=16, null=True, blank=True)
    airline_motive_details = models.CharField(max_length=64, null=True, blank=True)
    incident_description = models.TextField(null=True, blank=True)
    orthodromic_distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compensation_amount_eur = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Disruption(models.Model):
    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="disruption")
    disruption_type = models.CharField(max_length=32, choices=DisruptionType.choices)
    cancellation_notice_timing = models.CharField(max_length=32, null=True, blank=True)
    delay_arrival_timing = models.CharField(max_length=32, null=True, blank=True)
    denied_boarding_voluntary = models.CharField(max_length=16, null=True, blank=True)
    denied_boarding_reason = models.CharField(max_length=64, null=True, blank=True)
    airline_motive_known = models.CharField(max_length=16, null=True, blank=True)
    airline_motive_details = models.CharField(max_length=64, null=True, blank=True)
    incident_description = models.TextField()


class FlightSegment(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="flight_segments")
    sequence_number = models.PositiveSmallIntegerField()
    departure_airport_code = models.CharField(max_length=3)
    arrival_airport_code = models.CharField(max_length=3)
    flight_number = models.CharField(max_length=20)
    flight_date = models.DateField()
    airline = models.CharField(max_length=120)
    is_problem_flight = models.BooleanField(default=False)


class CaseDocument(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    file = models.FileField(upload_to="case_documents/%Y/%m/%d")
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
