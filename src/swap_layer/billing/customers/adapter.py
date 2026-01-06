from abc import abstractmethod
from typing import Dict, Any, Optional


class CustomerAdapter:
    """
    Abstract base class for customer management operations.
    This subdomain handles all customer-related operations.
    """
    
    @abstractmethod
    def create_customer(
        self, 
        email: str, 
        name: Optional[str] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
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
        email: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update customer details.
        
        Returns:
            Dict with updated customer data
        """
        pass

    @abstractmethod
    def delete_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Delete a customer from the provider.
        
        Returns:
            Dict with keys: id, deleted
        """
        pass
