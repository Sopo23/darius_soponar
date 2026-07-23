# CASE_01 Backend Design

## Overview

This document defines the backend design for `CASE_01` of the AirAssist application.

The feature allows a passenger to submit a compensation case request by completing the supported sections of the intake form. The first implementation covers backend-only behavior using Django, Django REST Framework, and PostgreSQL-compatible persistence.

This scope implements case intake only. It does not implement disruption details or disruption motives from parts 2 and 3 of the form. It also does not implement automatic eligibility decisioning. Every newly created case starts with status `NEW`.

## Scope

### In scope

- Public and authenticated passenger case creation
- Automatic passenger account creation for anonymous submissions
- Random temporary password assignment for newly created accounts
- Email notification prompting the passenger to change the assigned password
- Case persistence with status workflow initialization
- Flight itinerary and flight segment capture
- Problem flight selection and validation
- Passenger details capture
- GDPR consent enforcement
- Required document upload validation for boarding pass and ID/passport
- Airport code lookup through an external integration adapter
- Backend architecture organized around model, service, and view layers

### Out of scope

- Frontend implementation
- Disruption details and disruption motives from `CASE_03`
- Eligibility rules that set `VALID` or `INVALID`
- Staff assignment flows
- Passenger case comments
- Passenger case history retrieval
- Document download endpoints
- Cloud/object storage integration

## Business Requirements

The backend must support a case entry workflow with these rules:

- Passengers can access the case entry form whether they are registered or not.
- If a passenger submits a case without an existing account, the backend creates an account using the submitted email address.
- Newly auto-created accounts receive a random temporary password and an email prompting the passenger to change it.
- All implemented fields are mandatory.
- Airport codes must be loaded automatically through backend integration.
- A passenger may add up to 4 connecting flights.
- Exactly one flight must be marked as the problem flight.
- GDPR consent is mandatory before submission.
- Each flight requires flight number, flight date, and airline.
- Required uploads are boarding pass and ID/passport.
- Accepted upload formats are PDF, JPG, and JPEG.
- Maximum file size is 5 MB per uploaded file.
- A newly created case must start in status `NEW`.
- Supported statuses for the model are `NEW`, `VALID`, `ASSIGNED`, and `INVALID`.

## Architecture

The backend will be implemented as a modular monolith using a single Django project with Django REST Framework.

### Recommended structure

- One Django project for configuration and URL wiring
- One main `cases` app containing the `CASE_01` domain
- A small integration module for airport lookup
- Clear separation between persistence, orchestration, and transport layers

### Layer responsibilities

#### Models

Models define the persistent domain entities and relationships.

- `Case`: aggregate root for a compensation request
- `FlightSegment`: one row per main or connecting flight
- `CaseDocument`: uploaded documents for a case
- Django user model or custom user model: passenger account ownership
- Optional passenger profile extension if later stories require reusable personal data

#### Services

Services encapsulate business logic and transactional orchestration.

Primary responsibilities:

- Resolve existing passenger or create a new account
- Generate a random temporary password for newly created users
- Trigger password-change email workflow
- Validate itinerary and problem-flight rules
- Validate uploads and consent rules beyond serializer shape checks
- Validate airport codes through the integration boundary
- Persist case, flights, and documents atomically

#### Views

Views expose DRF endpoints and delegate business logic to services.

Primary responsibilities:

- Parse and authenticate requests
- Call serializers for request validation
- Call services for orchestration
- Return normalized API responses and error payloads

## Data Model

### User

The system uses Django authentication for passenger accounts.

Required behavior:

- Registered passengers can create cases under their existing account.
- Anonymous passengers trigger account creation during case submission.
- User creation is keyed by email address.
- New accounts receive a random temporary password.
- A notification email asks the passenger to change the password.

Implementation note:

- Use email as the canonical passenger identifier for case linkage.
- The first slice may use Django's default user model extended with email constraints, or a custom user model if the project is scaffolded from scratch.

### Case

The `Case` model is the aggregate root.

Suggested fields:

- `id`
- `owner` -> foreign key to user
- `status` -> enum with `NEW`, `VALID`, `ASSIGNED`, `INVALID`
- `contact_email`
- `gdpr_consent` -> boolean
- `gdpr_consented_at` -> datetime
- `created_at`
- `updated_at`

Rules:

- `status` defaults to `NEW`
- `gdpr_consent` must be true on creation

### FlightSegment

Stores the primary flight and up to four connecting flights.

Suggested fields:

- `id`
- `case` -> foreign key to case
- `sequence_number`
- `departure_airport_code`
- `arrival_airport_code`
- `flight_number`
- `flight_date`
- `airline`
- `is_problem_flight`

Rules:

- Minimum one flight segment required
- Maximum five total segments allowed
- Exactly one segment must have `is_problem_flight = true`

### CaseDocument

Stores uploaded files and metadata.

Suggested fields:

- `id`
- `case` -> foreign key to case
- `document_type` -> enum with `BOARDING_PASS`, `ID_OR_PASSPORT`
- `file`
- `original_filename`
- `content_type`
- `file_size`
- `created_at`

Rules:

- Both document types are required for creation
- Allowed content types and extensions: PDF, JPG, JPEG
- Maximum file size is 5 MB per file

## API Design

### POST /api/cases/

Creates a new compensation case in status `NEW`.

#### Access

- Public access allowed
- Authenticated access allowed

#### Behavior

- Accepts multipart form data or an equivalent nested payload format compatible with document uploads
- Validates all mandatory fields for the implemented sections
- Creates or reuses a passenger account based on email
- Validates airports through the airport lookup integration
- Creates the case and all child records in one transaction

#### Request content

The request includes:

- itinerary and flight segments
- email/compliance fields
- flight details
- passenger details
- boarding pass upload
- ID/passport upload

The request excludes:

- disruption details
- disruption motives

#### Response content

The response should return:

- case identifier
- status
- created timestamp
- owner identifier or ownership metadata
- flight segment data
- document metadata

### GET /api/airports/?search=

Provides airport lookup suggestions by calling AirportGap through a backend adapter.

#### Behavior

- The frontend queries the backend, not the third-party API directly.
- The backend transforms the AirportGap response into an internal response shape.
- The backend hides provider-specific failures behind controlled error responses.

## Validation Rules

Validation is split between serializers and services.

### Serializer validation

- Required fields exist
- Request structure is valid
- Required files are present
- File types are allowed
- File sizes are within the 5 MB limit

### Service validation

- Passenger account is resolved or created correctly
- Maximum of four connecting flights is enforced
- Maximum of five total segments is enforced
- Exactly one problem flight is enforced
- GDPR consent is true
- Airport codes are valid according to the integration adapter
- Child records are created consistently within a transaction

## Integration Design

### Airport lookup

The backend integrates with AirportGap using a dedicated adapter module.

Responsibilities:

- Build outbound requests
- Parse provider responses
- Map provider data into an internal DTO or serializer-friendly structure
- Raise domain-friendly integration errors on provider failure or invalid lookup responses

The adapter boundary keeps the rest of the application independent from the third-party schema and makes the integration easy to mock during tests.

### Email workflow

The backend sends an email when an anonymous submission creates a new account.

Responsibilities:

- Inform the passenger that an account was created
- Prompt the passenger to change the temporary password
- Keep the email-sending mechanism abstracted behind a service boundary for testing and later provider changes

## Data Flow

### Anonymous passenger flow

1. Passenger submits the case form.
2. Serializer validates request shape and file constraints.
3. Service checks whether a user exists for the submitted email.
4. If no user exists, service creates a new account with a random temporary password.
5. Service validates airport codes through the airport adapter.
6. Service validates itinerary, problem flight, and GDPR rules.
7. Service creates the case, flight segments, and documents inside one database transaction.
8. Service triggers the password-change email for the new account.
9. API returns the created case in status `NEW`.

### Authenticated passenger flow

1. Passenger submits the case form while authenticated.
2. Serializer validates request shape and file constraints.
3. Service reuses the authenticated user account.
4. Service validates airport codes through the airport adapter.
5. Service validates itinerary, problem flight, and GDPR rules.
6. Service creates the case, flight segments, and documents inside one database transaction.
7. API returns the created case in status `NEW`.

## Error Handling

The API returns predictable JSON validation errors and controlled integration failures.

### Validation failures

- Missing required fields return `400 Bad Request`
- Missing consent returns `400 Bad Request`
- Missing or invalid documents return `400 Bad Request`
- Invalid problem-flight selection returns `400 Bad Request`
- Too many connecting flights return `400 Bad Request`

### Integration failures

- Invalid airport lookup result returns `400 Bad Request`
- Airport provider unavailability returns `503 Service Unavailable`

### Transaction guarantees

- User creation, case creation, flight persistence, and document persistence should be coordinated so partial writes are avoided for the case aggregate.
- If any creation step fails, the case transaction is rolled back.

## Security And Authorization

- `POST /api/cases/` allows anonymous and authenticated submissions
- Passenger account ownership is attached to the created case
- Future passenger-only retrieval endpoints will use ownership checks
- File validation must reject unsupported types and oversize uploads
- Sensitive provider and email settings must come from environment configuration

## Testing Strategy

### Model tests

- Status default is `NEW`
- Entity relationships work correctly
- Enum values are enforced

### Service tests

- Anonymous submission creates a user and case
- Authenticated submission reuses existing user
- New user receives temporary-password workflow trigger
- More than four connecting flights is rejected
- Missing or multiple problem flights is rejected
- Missing GDPR consent is rejected
- Invalid file type is rejected
- Oversized file is rejected
- Airport validation failures are handled correctly
- Aggregate creation is atomic

### API tests

- Public case creation works
- Authenticated case creation works
- Multipart upload handling works
- Validation error payloads are stable
- Airport lookup endpoint returns normalized responses

### Test isolation

- AirportGap calls are mocked
- Email sending is mocked

## Initial Implementation Guidance

The first implementation should prioritize a working backend slice with clean boundaries rather than early optimization.

Recommended implementation order:

1. Scaffold Django project and dependencies
2. Configure PostgreSQL-ready settings with environment variables
3. Create `cases` app and domain models
4. Implement serializers for nested case creation
5. Implement services for account creation, airport validation, and transactional case creation
6. Add API views and URL wiring
7. Add tests for model, service, and API layers

## Decisions Captured

- Backend stack: Django + Django REST Framework
- Database: PostgreSQL
- Form creation is allowed for both anonymous and registered passengers
- Anonymous submission creates a passenger account automatically
- New account receives a random temporary password and password-change email
- Airport lookup uses AirportGap through a backend adapter
- File storage uses normal Django file storage with database metadata
- `CASE_01` only creates cases with status `NEW`
- Architecture follows model, service, and view separation
