from abc import abstractmethod
from decimal import Decimal
from typing import Any


class ProductAdapter:
    """
    Abstract base class for product and pricing operations.
    This subdomain handles product catalog and pricing management.

    Note: This is a placeholder for future implementation.
    """

    @abstractmethod
    def create_product(
        self, name: str, description: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a product.

        Returns:
            Dict with keys: id, name, description, metadata
        """
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> dict[str, Any]:
        """
        Retrieve product details.

        Returns:
            Dict with product information
        """
        pass

    @abstractmethod
    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update a product.

        Returns:
            Dict with updated product data
        """
        pass

    @abstractmethod
    def list_products(self, limit: int = 10, active: bool | None = None) -> list[dict[str, Any]]:
        """
        List products.

        Args:
            limit: Maximum number of results
            active: Filter by active status

        Returns:
            List of product dicts
        """
        pass

    @abstractmethod
    def create_price(
        self,
        product_id: str,
        amount: Decimal,
        currency: str,
        recurring: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a price for a product.

        Args:
            product_id: The product ID
            amount: Amount in smallest currency unit
            currency: Three-letter currency code
            recurring: Dict with 'interval' (day, week, month, year) and optional 'interval_count'

        Returns:
            Dict with keys: id, product_id, amount, currency, recurring
        """
        pass

    @abstractmethod
    def get_price(self, price_id: str) -> dict[str, Any]:
        """
        Retrieve price details.

        Returns:
            Dict with price information
        """
        pass

    @abstractmethod
    def list_prices(self, product_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """
        List prices.

        Args:
            product_id: Optional product ID filter
            limit: Maximum number of results

        Returns:
            List of price dicts
        """
        pass
