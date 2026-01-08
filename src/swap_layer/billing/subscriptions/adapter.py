from abc import abstractmethod
from typing import Any


class SubscriptionAdapter:
    """
    Abstract base class for subscription management operations.
    This subdomain handles all subscription-related operations.
    """

    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: dict[str, Any] | None = None,
        trial_period_days: int | None = None,
    ) -> dict[str, Any]:
        """
        Create a subscription for a customer.

        Returns:
            Dict with keys: id, customer_id, status, current_period_end,
            cancel_at_period_end, items
        """
        pass

    @abstractmethod
    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        """
        Retrieve subscription details.

        Returns:
            Dict with keys: id, customer_id, status, current_period_start,
            current_period_end, cancel_at_period_end
        """
        pass

    @abstractmethod
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update a subscription (e.g., change plan).

        Returns:
            Dict with updated subscription data
        """
        pass

    @abstractmethod
    def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> dict[str, Any]:
        """
        Cancel a subscription.

        Args:
            at_period_end: If True, cancel at end of billing period.
                          If False, cancel immediately.

        Returns:
            Dict with keys: id, status, cancel_at_period_end
        """
        pass

    @abstractmethod
    def list_subscriptions(
        self, customer_id: str, status: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        List subscriptions for a customer.

        Args:
            customer_id: The customer ID
            status: Optional status filter (active, canceled, etc.)
            limit: Maximum number of results

        Returns:
            List of subscription dicts
        """
        pass
