from typing import Any

import stripe
from django.conf import settings

from ..adapter import (
    IdentityVerificationConnectionError,
    IdentityVerificationError,
    IdentityVerificationProviderAdapter,
    IdentityVerificationSessionNotFoundError,
    IdentityVerificationValidationError,
)


class StripeIdentityVerificationProvider(IdentityVerificationProviderAdapter):
    """
    Stripe implementation of the IdentityVerificationProviderAdapter.
    """

    def __init__(self):
        if not hasattr(settings, "STRIPE_SECRET_KEY") or not settings.STRIPE_SECRET_KEY:
            raise ValueError("Stripe secret key not configured")
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def get_vendor_client(self) -> Any:
        """
        Return the underlying Stripe client/SDK for advanced usage.
        Use this escape hatch when you need to access Stripe-specific features
        that are not exposed by the abstraction layer.
        """
        return stripe

    def create_verification_session(
        self, user: Any, verification_type: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a verification session with Stripe.

        Args:
            user: The user to verify
            verification_type: Type of verification (e.g., 'document')
            options: Optional dict with return_url, metadata, email

        Returns:
            Dict with session details
        """
        try:
            default_options = {
                "type": verification_type,
                "metadata": {
                    "user_id": str(user.id),
                    "username": getattr(user, "username", ""),
                },
            }

            if options:
                # Handle return_url specifically if passed in options
                if "return_url" in options and options["return_url"]:
                    default_options["return_url"] = options["return_url"]

                # Handle provided_details (e.g. email)
                if "email" in options and options["email"]:
                    default_options["provided_details"] = {"email": options["email"]}

                # Merge other options
                if "metadata" in options:
                    default_options["metadata"].update(options["metadata"])

            session = stripe.identity.VerificationSession.create(**default_options)

            return {
                "provider_session_id": session.id,
                "client_secret": session.client_secret,
                "status": session.status,
                "type": session.type,
                "url": session.url,
                "created": session.created,
            }
        except stripe.error.InvalidRequestError as e:
            raise IdentityVerificationValidationError(f"Invalid request: {str(e)}")
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def get_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve session details from Stripe.

        Args:
            session_id: The Stripe session ID

        Returns:
            Dict with session details
        """
        try:
            session = stripe.identity.VerificationSession.retrieve(
                session_id, expand=["verified_outputs", "last_error"]
            )

            result = {
                "id": session.id,
                "status": session.status,
                "type": session.type,
                "created": session.created,
                "metadata": session.metadata,
                "last_verification_report": session.last_verification_report,
            }

            if session.verified_outputs:
                result["verified_outputs"] = session.verified_outputs

            if session.last_error:
                result["last_error"] = session.last_error

            return result
        except stripe.error.InvalidRequestError as e:
            if "No such" in str(e):
                raise IdentityVerificationSessionNotFoundError(f"Session not found: {session_id}")
            raise IdentityVerificationValidationError(f"Invalid request: {str(e)}")
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def list_verification_sessions(
        self, limit: int = 10, status: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        List verification sessions from Stripe.

        Args:
            limit: Maximum number of results
            status: Optional status filter
            **kwargs: Additional Stripe-specific filters

        Returns:
            Dict with session data
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status

            # Add optional filters from kwargs (Stripe specific)
            if "created_gte" in kwargs and kwargs["created_gte"]:
                params["created[gte]"] = kwargs["created_gte"]
            # Note: Stripe doesn't directly filter by metadata in list
            # We rely on our DB for user-specific listing

            sessions = stripe.identity.VerificationSession.list(**params)
            return sessions
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def cancel_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Cancel a verification session in Stripe.

        Args:
            session_id: The Stripe session ID

        Returns:
            Dict with id and status
        """
        try:
            session = stripe.identity.VerificationSession.cancel(session_id)
            return {
                "id": session.id,
                "status": session.status,
            }
        except stripe.error.InvalidRequestError as e:
            if "No such" in str(e):
                raise IdentityVerificationSessionNotFoundError(f"Session not found: {session_id}")
            raise IdentityVerificationValidationError(f"Invalid request: {str(e)}")
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def redact_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Redact a verification session in Stripe to remove PII.

        Args:
            session_id: The Stripe session ID

        Returns:
            Dict with id and status
        """
        try:
            session = stripe.identity.VerificationSession.redact(session_id)
            return {
                "id": session.id,
                "status": session.status,
            }
        except stripe.error.InvalidRequestError as e:
            if "No such" in str(e):
                raise IdentityVerificationSessionNotFoundError(f"Session not found: {session_id}")
            raise IdentityVerificationValidationError(f"Invalid request: {str(e)}")
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def get_verification_report(self, report_id: str) -> dict[str, Any]:
        """
        Retrieve a verification report from Stripe.

        Args:
            report_id: The Stripe report ID

        Returns:
            Dict with report details
        """
        try:
            report = stripe.identity.VerificationReport.retrieve(report_id)
            return {
                "id": report.id,
                "type": report.type,
                "created": report.created,
                "document": report.document,
                "id_number": report.id_number,
                "selfie": report.selfie,
                "verification_session": report.verification_session,
                "options": report.options,
            }
        except stripe.error.InvalidRequestError as e:
            if "No such" in str(e):
                raise IdentityVerificationSessionNotFoundError(f"Report not found: {report_id}")
            raise IdentityVerificationValidationError(f"Invalid request: {str(e)}")
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def get_verification_insights(self, session_id: str) -> dict[str, Any]:
        """
        Get insights from a verification session.

        Args:
            session_id: The Stripe session ID

        Returns:
            Dict with session insights including checks performed
        """
        try:
            session_data = self.get_verification_session(session_id)

            insights = {
                "session_id": session_id,
                "status": session_data.get("status"),
                "verified_outputs": session_data.get("verified_outputs"),
                "checks_performed": [],
                "risk_signals": [],
            }

            # Re-fetch to ensure we have the report expanded
            session = stripe.identity.VerificationSession.retrieve(
                session_id, expand=["last_verification_report"]
            )

            report = session.last_verification_report

            if report:
                # Document checks
                if hasattr(report, "document") and report.document:
                    doc = report.document
                    insights["checks_performed"].append(
                        {
                            "type": "document",
                            "status": doc.status,
                            "error": doc.error,
                        }
                    )

                # Selfie checks
                if hasattr(report, "selfie") and report.selfie:
                    selfie = report.selfie
                    insights["checks_performed"].append(
                        {
                            "type": "selfie",
                            "status": selfie.status,
                            "error": selfie.error,
                        }
                    )

                # ID number checks
                if hasattr(report, "id_number") and report.id_number:
                    id_num = report.id_number
                    insights["checks_performed"].append(
                        {
                            "type": "id_number",
                            "status": id_num.status,
                            "error": id_num.error,
                        }
                    )

            return insights
        except IdentityVerificationError:
            raise
        except stripe.error.APIConnectionError as e:
            raise IdentityVerificationConnectionError(f"Connection error: {str(e)}")
        except stripe.error.StripeError as e:
            raise IdentityVerificationError(f"Stripe error: {str(e)}")

    def handle_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Verify and parse a webhook payload from Stripe.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature header

        Returns:
            Dict with parsed event data
        """
        endpoint_secret = getattr(settings, "STRIPE_IDENTITY_WEBHOOK_SECRET", None)

        try:
            event = stripe.Webhook.construct_event(payload, signature, endpoint_secret)
            return event
        except ValueError as e:
            raise IdentityVerificationValidationError(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise IdentityVerificationError(f"Invalid signature: {str(e)}")
