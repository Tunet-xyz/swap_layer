from abc import abstractmethod
from typing import Any


class SubscriptionAdapter:
    """Abstract interface for subscription lifecycle operations."""

    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_period_days: int | None = None,
        items: list[dict[str, Any]] | None = None,
        quantity: int | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def update_subscription(
        self,
        subscription_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
        quantity: int | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def pause_subscription(
        self,
        subscription_id: str,
        behavior: str = "void",
        resumes_at: int | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def resume_subscription(
        self,
        subscription_id: str,
        billing_cycle_anchor: str | None = None,
        proration_behavior: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_subscriptions(
        self, customer_id: str, status: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        pass
