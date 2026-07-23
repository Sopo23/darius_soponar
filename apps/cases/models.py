from django.conf import settings
from django.db import models

from .constants import CaseStatus, DocumentType


class Case(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cases")
    status = models.CharField(max_length=20, choices=CaseStatus.choices, default=CaseStatus.NEW)
    contact_email = models.EmailField()
    gdpr_consent = models.BooleanField()
    gdpr_consented_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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
