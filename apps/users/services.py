from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


class PasswordResetService:
    def send_reset_email(self, *, email: str) -> None:
        user_model = get_user_model()
        user = user_model.objects.filter(email__iexact=email, is_active=True).first()
        if user is None:
            return

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"

        send_mail(
            subject="Reset your AirAssist password",
            message=(
                "We received a request to reset your AirAssist password. "
                f"Use this link to set a new password: {reset_link}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    def reset_password(self, *, uid: str, token: str, new_password: str):
        user = self._get_user_from_uid(uid)
        if user is None or not default_token_generator.check_token(user, token):
            return None

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        return user

    def _get_user_from_uid(self, uid: str):
        user_model = get_user_model()
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            return user_model.objects.filter(pk=user_id, is_active=True).first()
        except (TypeError, ValueError, OverflowError):
            return None
