from abc import abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal


class ProductAdapter:
    """
    Abstract base class for product and pricing operations.
    This subdomain handles product catalog and pricing management.
    
    Note: This is a placeholder for future implementation.
    """
    
    @abstractmethod
    def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a product.
        
        Returns:
            Dict with keys: id, name, description, metadata
        """
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> Dict[str, Any]:
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
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a product.
        
        Returns:
            Dict with updated product data
        """
        pass

    @abstractmethod
    def list_products(
        self,
        limit: int = 10,
        active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
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
        recurring: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
    def get_price(self, price_id: str) -> Dict[str, Any]:
        """
        Retrieve price details.
        
        Returns:
            Dict with price information
        """
        pass

    @abstractmethod
    def list_prices(
        self,
        product_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List prices.
        
        Args:
            product_id: Optional product ID filter
            limit: Maximum number of results
            
        Returns:
            List of price dicts
        """
        pass
