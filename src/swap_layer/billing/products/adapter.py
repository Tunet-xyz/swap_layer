from abc import abstractmethod
from decimal import Decimal
from typing import Any


class ProductAdapter:
    """Abstract interface for product and pricing operations."""

    @abstractmethod
    def create_product(
        self,
        name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_products(self, limit: int = 10, active: bool | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def create_price(
        self,
        product_id: str,
        amount: Decimal,
        currency: str,
        recurring: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        lookup_key: str | None = None,
        nickname: str | None = None,
        tax_behavior: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_price(self, price_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_prices(self, product_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        pass
