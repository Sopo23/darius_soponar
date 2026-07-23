from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cases.serializers import AirportQuerySerializer, AirportResultSerializer, CaseCreateSerializer
from apps.cases.services.account_service import PassengerAccountService
from apps.cases.services.airport_service import (
    AirportLookupError,
    AirportProviderUnavailableError,
    AirportService,
)
from apps.cases.services.case_service import CaseCreationService


class CaseCreateView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = CaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = CaseCreationService(
            account_service=PassengerAccountService(),
            airport_service=AirportService(base_url=settings.AIRPORTGAP_BASE_URL),
        )

        try:
            case = service.create_case(
                authenticated_user=request.user if request.user.is_authenticated else None,
                validated_data=serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(detail=exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        except AirportProviderUnavailableError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AirportLookupError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_payload = {
            "id": case.id,
            "status": case.status,
            "contact_email": case.contact_email,
            "created_at": case.created_at,
            "flight_segments": [
                {
                    "sequence_number": flight.sequence_number,
                    "departure_airport_code": flight.departure_airport_code,
                    "arrival_airport_code": flight.arrival_airport_code,
                    "flight_number": flight.flight_number,
                    "flight_date": flight.flight_date,
                    "airline": flight.airline,
                    "is_problem_flight": flight.is_problem_flight,
                }
                for flight in case.flight_segments.order_by("sequence_number")
            ],
            "documents": [
                {
                    "document_type": document.document_type,
                    "original_filename": document.original_filename,
                    "file_size": document.file_size,
                }
                for document in case.documents.order_by("id")
            ],
        }
        return Response(response_payload, status=status.HTTP_201_CREATED)


class AirportSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = AirportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service = AirportService(base_url=settings.AIRPORTGAP_BASE_URL)
        try:
            airports = service.search(serializer.validated_data["search"])
        except AirportProviderUnavailableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except AirportLookupError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = AirportResultSerializer(airports, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
