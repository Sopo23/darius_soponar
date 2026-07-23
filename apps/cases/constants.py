from django.db import models


class CaseStatus(models.TextChoices):
    NEW = "NEW", "New"
    VALID = "VALID", "Valid"
    ASSIGNED = "ASSIGNED", "Assigned"
    INVALID = "INVALID", "Invalid"


class DocumentType(models.TextChoices):
    BOARDING_PASS = "BOARDING_PASS", "Boarding Pass"
    ID_OR_PASSPORT = "ID_OR_PASSPORT", "ID or Passport"


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg"}
MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024
MAX_CONNECTING_FLIGHTS = 4
MAX_TOTAL_FLIGHTS = 5
