# CASE_01 Backend Implementation Plan

> **Execution:** Use subagent-driven development to implement this plan task-by-task.

**Goal:** Build the first backend slice of AirAssist that lets anonymous or authenticated passengers create a compensation case with flights, required documents, GDPR consent, and automatic passenger account creation.

**Architecture:** Use a Django modular monolith with Django REST Framework and PostgreSQL-ready settings. Keep persistence in focused models, orchestration in service classes, and transport logic in serializers and API views, with a small adapter around the AirportGap integration.

**Tech Stack:** Python, Django, Django REST Framework, PostgreSQL, pytest, pytest-django, requests

**Design Spec:** `documentation/spec-driven/specs/2026-07-23-case-01-backend-design.md`

---

## File Structure

- Create: `requirements.txt` — backend dependencies for Django, DRF, PostgreSQL, testing, and environment configuration
- Create: `.env.example` — local environment variables for Django secret key, debug flag, database connection, email backend, and AirportGap base URL
- Create: `manage.py` — Django entry point
- Create: `airassist_backend/__init__.py` — package marker
- Create: `airassist_backend/asgi.py` — ASGI entry point
- Create: `airassist_backend/wsgi.py` — WSGI entry point
- Create: `airassist_backend/settings.py` — project settings with custom user model, DRF config, media config, and PostgreSQL-ready database settings
- Create: `airassist_backend/urls.py` — root URL routing for health/admin/API/media
- Create: `airassist_backend/api_urls.py` — API-only URL routing
- Create: `apps/__init__.py` — apps package marker
- Create: `apps/users/__init__.py` — users app package marker
- Create: `apps/users/apps.py` — users app config
- Create: `apps/users/models.py` — custom email-based user model and manager
- Create: `apps/users/admin.py` — admin registration for the custom user model
- Create: `apps/users/migrations/__init__.py` — migrations package marker
- Create: `apps/cases/__init__.py` — cases app package marker
- Create: `apps/cases/apps.py` — cases app config
- Create: `apps/cases/models.py` — case, flight segment, and case document models
- Create: `apps/cases/admin.py` — admin registration for case domain models
- Create: `apps/cases/constants.py` — shared enums and upload validation constants
- Create: `apps/cases/services/__init__.py` — services package marker
- Create: `apps/cases/services/account_service.py` — resolve or create passenger accounts and trigger onboarding email
- Create: `apps/cases/services/airport_service.py` — AirportGap adapter and airport validation methods
- Create: `apps/cases/services/case_service.py` — transactional case creation orchestration
- Create: `apps/cases/serializers.py` — nested serializers for case creation and airport lookup responses
- Create: `apps/cases/views.py` — DRF views for case creation and airport search
- Create: `apps/cases/urls.py` — cases API routes
- Create: `apps/cases/tests/__init__.py` — tests package marker
- Create: `apps/cases/tests/conftest.py` — reusable test fixtures for users, files, and request payloads
- Create: `apps/cases/tests/test_models.py` — model behavior tests
- Create: `apps/cases/tests/test_services.py` — service-layer business rule tests
- Create: `apps/cases/tests/test_api.py` — API tests for case creation and airport search
- Create: `pytest.ini` — pytest configuration for Django

### Task 1: Project Foundation And User Authentication Base

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `manage.py`
- Create: `airassist_backend/__init__.py`
- Create: `airassist_backend/asgi.py`
- Create: `airassist_backend/wsgi.py`
- Create: `airassist_backend/settings.py`
- Create: `airassist_backend/urls.py`
- Create: `airassist_backend/api_urls.py`
- Create: `apps/__init__.py`
- Create: `apps/users/__init__.py`
- Create: `apps/users/apps.py`
- Create: `apps/users/models.py`
- Create: `apps/users/admin.py`
- Create: `apps/users/migrations/__init__.py`

**Requirements:**
- Scaffold a runnable Django project from scratch in the repository root.
- Configure Django REST Framework and PostgreSQL-ready database settings via environment variables.
- Define a custom user model that uses email as the unique login field.
- Keep settings ready for anonymous and authenticated API access.
- Configure media storage for uploaded files and a console email backend for local development.

**Implementation:**

```python
# requirements.txt
Django>=5.1,<5.2
djangorestframework>=3.15,<3.16
psycopg[binary]>=3.2,<3.3
python-dotenv>=1.0,<2.0
requests>=2.32,<3.0
pytest>=8.3,<9.0
pytest-django>=4.9,<5.0
```

```python
# apps/users/models.py
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()
```

```python
# airassist_backend/settings.py
AUTH_USER_MODEL = "users.User"
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.users",
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}
```

**Testing:**

```python
def test_user_creation_uses_email_as_login(django_user_model):
    user = django_user_model.objects.create_user(
        email="traveler@example.com",
        password="changeme123",
    )

    assert user.email == "traveler@example.com"
    assert user.check_password("changeme123") is True
```

**Verification:**
- Run `python -m pip install -r requirements.txt`.
- Run `python manage.py check` and expect Django system checks to pass.
- Run `python manage.py makemigrations users` and expect a migration for the custom user model.

### Task 2: Case Domain Models And Admin Registration

**Files:**
- Create: `apps/cases/__init__.py`
- Create: `apps/cases/apps.py`
- Create: `apps/cases/constants.py`
- Create: `apps/cases/models.py`
- Create: `apps/cases/admin.py`
- Create: `apps/cases/migrations/__init__.py`
- Modify: `airassist_backend/settings.py`

**Requirements:**
- Add the `cases` app to project settings.
- Model the `Case`, `FlightSegment`, and `CaseDocument` entities.
- Represent statuses as `NEW`, `VALID`, `ASSIGNED`, and `INVALID`.
- Enforce clear database relationships between user, case, flights, and documents.
- Keep model-level defaults aligned with the spec, especially default case status `NEW`.

**Implementation:**

```python
# apps/cases/constants.py
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
```

```python
# apps/cases/models.py
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
```

**Testing:**

```python
def test_case_defaults_to_new_status(user_factory):
    case = Case.objects.create(
        owner=user_factory(),
        contact_email="traveler@example.com",
        gdpr_consent=True,
        gdpr_consented_at=timezone.now(),
    )

    assert case.status == CaseStatus.NEW
```

**Verification:**
- Run `python manage.py makemigrations users cases` and expect migrations for case entities.
- Run `python manage.py migrate` and expect all project migrations to apply cleanly.
- Run `python manage.py check` and expect the cases app to load without errors.

### Task 3: Service Layer, Airport Integration, And Nested Serializers

**Files:**
- Create: `apps/cases/services/__init__.py`
- Create: `apps/cases/services/account_service.py`
- Create: `apps/cases/services/airport_service.py`
- Create: `apps/cases/services/case_service.py`
- Create: `apps/cases/serializers.py`
- Modify: `airassist_backend/settings.py`

**Requirements:**
- Implement a service to resolve or create a passenger account from email.
- Generate a random temporary password for new users and send a password-change prompt email.
- Implement an AirportGap adapter that searches airports and validates airport codes.
- Add nested serializers for flights, passenger details, compliance data, and file uploads.
- Enforce all `CASE_01` business rules in the service layer: required files, max 4 connections, exactly one problem flight, GDPR consent, and airport validation.
- Persist the case aggregate in a single transaction.

**Implementation:**

```python
# apps/cases/services/account_service.py
from dataclasses import dataclass
from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.core.mail import send_mail


@dataclass
class AccountResolutionResult:
    user: object
    created: bool


class PassengerAccountService:
    def resolve_or_create(self, email, first_name, last_name):
        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=email).first()
        if user:
            return AccountResolutionResult(user=user, created=False)

        temporary_password = token_urlsafe(12)
        user = user_model.objects.create_user(
            email=email,
            password=temporary_password,
            first_name=first_name,
            last_name=last_name,
        )
        send_mail(
            subject="Your AirAssist account was created",
            message=(
                "An AirAssist account was created for your compensation case. "
                f"Your temporary password is: {temporary_password}. "
                "Please change it after signing in."
            ),
            from_email=None,
            recipient_list=[email],
        )
        return AccountResolutionResult(user=user, created=True)
```

```python
# apps/cases/services/airport_service.py
import requests


class AirportLookupError(Exception):
    pass


class AirportService:
    def __init__(self, base_url, session=None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def search(self, query):
        response = self.session.get(f"{self.base_url}/api/airports", params={"q": query}, timeout=10)
        if response.status_code != 200:
            raise AirportLookupError("Airport provider unavailable")
        return response.json().get("data", [])

    def ensure_airport_exists(self, airport_code):
        results = self.search(airport_code)
        if not any(item.get("attributes", {}).get("iata") == airport_code for item in results):
            raise AirportLookupError(f"Airport code {airport_code} is invalid")
```

```python
# apps/cases/services/case_service.py
from django.db import transaction
from django.utils import timezone

from apps.cases.constants import DocumentType, MAX_CONNECTING_FLIGHTS, MAX_TOTAL_FLIGHTS
from apps.cases.models import Case, CaseDocument, FlightSegment


class CaseCreationService:
    def __init__(self, account_service, airport_service):
        self.account_service = account_service
        self.airport_service = airport_service

    @transaction.atomic
    def create_case(self, *, authenticated_user, validated_data):
        flights = validated_data.pop("flight_segments")
        documents = validated_data.pop("documents")
        passenger = validated_data.pop("passenger")

        if len(flights) - 1 > MAX_CONNECTING_FLIGHTS or len(flights) > MAX_TOTAL_FLIGHTS:
            raise ValueError("A passenger may add up to 4 connecting flights")

        if sum(1 for flight in flights if flight["is_problem_flight"]) != 1:
            raise ValueError("Exactly one problem flight must be selected")

        if validated_data["gdpr_consent"] is not True:
            raise ValueError("GDPR consent is required")

        for flight in flights:
            self.airport_service.ensure_airport_exists(flight["departure_airport_code"])
            self.airport_service.ensure_airport_exists(flight["arrival_airport_code"])

        owner = authenticated_user
        if owner is None:
            owner = self.account_service.resolve_or_create(
                email=passenger["email"],
                first_name=passenger["first_name"],
                last_name=passenger["last_name"],
            ).user

        case = Case.objects.create(
            owner=owner,
            contact_email=passenger["email"],
            gdpr_consent=True,
            gdpr_consented_at=timezone.now(),
        )
```

**Testing:**

```python
def test_anonymous_submission_creates_user_and_case(case_creation_service, valid_case_payload):
    result = case_creation_service.create_case(
        authenticated_user=None,
        validated_data=valid_case_payload,
    )

    assert result.owner.email == valid_case_payload["passenger"]["email"]
    assert result.flight_segments.count() == 1
    assert result.documents.count() == 2
```

```python
def test_multiple_problem_flights_are_rejected(case_creation_service, valid_case_payload):
    valid_case_payload["flight_segments"][0]["is_problem_flight"] = True
    valid_case_payload["flight_segments"].append({
        "sequence_number": 2,
        "departure_airport_code": "OTP",
        "arrival_airport_code": "CDG",
        "flight_number": "AF1089",
        "flight_date": date(2026, 7, 23),
        "airline": "Air France",
        "is_problem_flight": True,
    })

    with pytest.raises(ValueError, match="Exactly one problem flight"):
        case_creation_service.create_case(authenticated_user=None, validated_data=valid_case_payload)
```

**Verification:**
- Run `pytest apps/cases/tests/test_services.py -q` and expect service tests to pass.
- Run `python manage.py check` and expect service dependencies to import cleanly.

### Task 4: API Endpoints, URL Wiring, And End-To-End Backend Tests

**Files:**
- Create: `apps/cases/views.py`
- Create: `apps/cases/urls.py`
- Create: `apps/cases/tests/__init__.py`
- Create: `apps/cases/tests/conftest.py`
- Create: `apps/cases/tests/test_models.py`
- Create: `apps/cases/tests/test_services.py`
- Create: `apps/cases/tests/test_api.py`
- Create: `pytest.ini`
- Modify: `airassist_backend/api_urls.py`
- Modify: `airassist_backend/urls.py`

**Requirements:**
- Expose `POST /api/cases/` for case creation.
- Expose `GET /api/airports/?search=` for airport lookup.
- Allow anonymous and authenticated submissions for case creation.
- Return stable JSON responses for success and validation failures.
- Add tests that cover API creation, airport lookup, and key business-rule failures.

**Implementation:**

```python
# apps/cases/views.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cases.serializers import AirportQuerySerializer, CaseCreateSerializer
from apps.cases.services.account_service import PassengerAccountService
from apps.cases.services.airport_service import AirportLookupError, AirportService
from apps.cases.services.case_service import CaseCreationService


class CaseCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = CaseCreationService(
            account_service=PassengerAccountService(),
            airport_service=AirportService(base_url=settings.AIRPORTGAP_BASE_URL),
        )
        case = service.create_case(
            authenticated_user=request.user if request.user.is_authenticated else None,
            validated_data=serializer.validated_data,
        )
        return Response({"id": case.id, "status": case.status}, status=status.HTTP_201_CREATED)
```

```python
# apps/cases/urls.py
from django.urls import path

from apps.cases.views import AirportSearchView, CaseCreateView

urlpatterns = [
    path("cases/", CaseCreateView.as_view(), name="case-create"),
    path("airports/", AirportSearchView.as_view(), name="airport-search"),
]
```

```python
# apps/cases/tests/test_api.py
def test_public_case_creation_returns_201(api_client, multipart_case_payload, mocker):
    mocker.patch("apps.cases.services.airport_service.AirportService.ensure_airport_exists")
    mocker.patch("apps.cases.services.account_service.send_mail")

    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == 201
    assert response.data["status"] == "NEW"


def test_airport_search_returns_normalized_payload(api_client, mocker):
    mocker.patch(
        "apps.cases.services.airport_service.AirportService.search",
        return_value=[{"attributes": {"iata": "OTP", "name": "Henri Coanda"}}],
    )

    response = api_client.get("/api/airports/", {"search": "otp"})

    assert response.status_code == 200
    assert response.data[0]["code"] == "OTP"
```

**Testing:**

```python
def test_missing_gdpr_consent_returns_400(api_client, multipart_case_payload, mocker):
    multipart_case_payload["gdpr_consent"] = False
    response = api_client.post("/api/cases/", data=multipart_case_payload, format="multipart")

    assert response.status_code == 400
    assert "gdpr_consent" in response.data
```

**Verification:**
- Run `pytest -q` and expect all tests to pass.
- Run `python manage.py check` and expect project wiring to pass.
- Start the dev server with `python manage.py runserver` and verify `POST /api/cases/` and `GET /api/airports/` are routed.

## Self-Review

### Spec coverage

- Public and authenticated case creation is covered by Tasks 1, 3, and 4.
- Automatic passenger account creation and onboarding email are covered by Task 3.
- PostgreSQL-ready project setup is covered by Task 1.
- Case, flights, documents, and statuses are covered by Task 2.
- Airport lookup integration is covered by Tasks 3 and 4.
- Connecting-flight logic, problem-flight validation, GDPR enforcement, and file validation are covered by Tasks 3 and 4.
- Backend tests for model, service, and API layers are covered by Tasks 2, 3, and 4.

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain in tasks.

### Type consistency

- `User`, `Case`, `FlightSegment`, and `CaseDocument` names are consistent across tasks.
- `CaseCreationService.create_case` uses `authenticated_user` and `validated_data` consistently across snippets and tests.
- Status and document enum names match the design spec and planned responses.
