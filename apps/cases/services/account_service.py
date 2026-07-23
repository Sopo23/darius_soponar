from dataclasses import dataclass
from secrets import token_urlsafe

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction


@dataclass(slots=True)
class AccountResolutionResult:
    user: object
    created: bool


class PassengerAccountService:
    @transaction.atomic
    def resolve_or_create(self, *, email: str, first_name: str, last_name: str) -> AccountResolutionResult:
        user_model = get_user_model()
        normalized_email = user_model.objects.normalize_email(email)
        user = user_model.objects.filter(email__iexact=normalized_email).first()
        if user is not None:
            return AccountResolutionResult(user=user, created=False)

        temporary_password = token_urlsafe(12)
        user = user_model.objects.create_user(
            email=normalized_email,
            password=temporary_password,
            first_name=first_name,
            last_name=last_name,
            must_change_password=True,
        )

        send_mail(
            subject="Your AirAssist account was created",
            message=(
                "An AirAssist account was created for your compensation case. "
                f"Your temporary password is: {temporary_password}. "
                "Please sign in and change it as soon as possible."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[normalized_email],
        )

        return AccountResolutionResult(user=user, created=True)
