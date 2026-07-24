from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.cases.services.account_service import PassengerAccountService


class UserModelTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_user_creation_uses_email_as_login(self):
        user = self.user_model.objects.create_user(
            email="traveler@example.com",
            password="changeme123",
        )

        self.assertEqual(user.email, "traveler@example.com")
        self.assertTrue(user.check_password("changeme123"))
        self.assertEqual(user.USERNAME_FIELD, "email")

    def test_user_email_is_normalized(self):
        user = self.user_model.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="changeme123",
        )

        self.assertEqual(user.email, "Test@example.com")

    def test_create_user_without_email_raises_error(self):
        with self.assertRaisesMessage(ValueError, "Email is required"):
            self.user_model.objects.create_user(email="", password="changeme123")

    def test_create_superuser(self):
        superuser = self.user_model.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )

        self.assertEqual(superuser.email, "admin@example.com")
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.check_password("adminpass123"))

    def test_user_string_representation(self):
        user = self.user_model.objects.create_user(
            email="user@example.com",
            password="pass123",
        )

        self.assertEqual(str(user), "user@example.com")

    def test_auto_created_passenger_requires_password_change(self):
        result = PassengerAccountService().resolve_or_create(
            email="new-passenger@example.com",
            first_name="New",
            last_name="Passenger",
        )

        self.assertTrue(result.created)
        self.assertTrue(result.user.must_change_password)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_auto_created_passenger_sends_temporary_password_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            PassengerAccountService().resolve_or_create(
                email="new-passenger@example.com",
                first_name="New",
                last_name="Passenger",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new-passenger@example.com"])
        self.assertIn("Your temporary password is:", mail.outbox[0].body)


class UserAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            email="registered@example.com",
            password="password123",
            first_name="Registered",
            last_name="Passenger",
            must_change_password=True,
        )

    def test_login_returns_token_and_user_state(self):
        response = self.client.post(
            "/api/auth/login/",
            data={"email": "registered@example.com", "password": "password123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["email"], "registered@example.com")
        self.assertTrue(response.data["user"]["must_change_password"])

    def test_change_password_rotates_token_and_clears_flag(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(
            "/api/auth/change-password/",
            data={
                "current_password": "password123",
                "new_password": "newStrongPassword123",
                "new_password_confirmation": "newStrongPassword123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password("newStrongPassword123"))
        self.assertNotEqual(response.data["token"], token.key)

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_password_reset_request_returns_success(self):
        response = self.client.post(
            "/api/auth/password-reset-request/",
            data={"email": "registered@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("detail", response.data)

    def test_password_reset_confirm_changes_password_and_clears_flag(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            "/api/auth/password-reset-confirm/",
            data={
                "uid": uid,
                "token": token,
                "new_password": "anotherStrongPassword123",
                "new_password_confirmation": "anotherStrongPassword123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password("anotherStrongPassword123"))
        self.assertIn("token", response.data)

    def test_password_reset_confirm_rejects_invalid_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.post(
            "/api/auth/password-reset-confirm/",
            data={
                "uid": uid,
                "token": "invalid-token",
                "new_password": "anotherStrongPassword123",
                "new_password_confirmation": "anotherStrongPassword123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "The reset link is invalid or expired.")
