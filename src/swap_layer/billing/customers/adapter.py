from abc import abstractmethod
from typing import Any


class CustomerAdapter:
    """
    Abstract base class for customer management operations.
    This subdomain handles all customer-related operations.
    """

    @abstractmethod
    def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a customer in the payment provider.

        Returns:
            Dict with keys: id, email, name, created

        Raises:
            PaymentValidationError: If data is invalid
            PaymentConnectionError: If provider is unreachable
        """
        pass

    @abstractmethod
    def get_customer(self, customer_id: str) -> dict[str, Any]:
        """
        Retrieve customer details from the provider.

        Returns:
            Dict with keys: id, email, name, metadata
        """
        pass

    @abstractmethod
    def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update customer details.

        Returns:
            Dict with updated customer data
        """
        pass

    @abstractmethod
    def delete_customer(self, customer_id: str) -> dict[str, Any]:
        """
        Delete a customer from the provider.

        Returns:
            Dict with keys: id, deleted
        """
        pass
