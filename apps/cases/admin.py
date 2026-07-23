from django.contrib import admin

from .models import Case, CaseDocument, FlightSegment


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "status", "contact_email", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("contact_email", "owner__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FlightSegment)
class FlightSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "sequence_number", "flight_number", "departure_airport_code", "arrival_airport_code", "flight_date", "is_problem_flight")
    list_filter = ("is_problem_flight", "flight_date")
    search_fields = ("flight_number", "airline")


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "document_type", "original_filename", "file_size", "created_at")
    list_filter = ("document_type", "created_at")
    search_fields = ("original_filename",)
    readonly_fields = ("created_at",)
