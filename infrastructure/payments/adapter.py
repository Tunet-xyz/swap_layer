from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from decimal import Decimal


class PaymentError(Exception):
    """Base exception for all payment related errors."""
    pass

class PaymentValidationError(PaymentError):
    """Raised when input data is invalid (e.g. invalid email, negative amount)."""
    pass

class PaymentDeclinedError(PaymentError):
    """Raised when the payment was declined by the processor."""
    pass

class PaymentConnectionError(PaymentError):
    """Raised when connection to the payment provider fails."""
    pass

class ResourceNotFoundError(PaymentError):
    """Raised when a requested resource (customer, subscription) is not found."""
    pass


class PaymentProviderAdapter(ABC):
    """
    Abstract base class for Payment Providers (Stripe, PayPal, Square, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """
    @abstractmethod
    def get_vendor_client(self) -> Any:
        """
        Return the underlying vendor client/SDK for advanced usage.
        Use this escape hatch when you need to access provider-specific features
        that are not exposed by the abstraction layer.
        """
        pass
    # Customer Management
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

    # Subscription Management
    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        trial_period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription for a customer.
        
        Returns:
            Dict with keys: id, customer_id, status, current_period_end, 
            cancel_at_period_end, items
        """
        pass

    @abstractmethod
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
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
        price_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update a subscription (e.g., change plan).
        
        Returns:
            Dict with updated subscription data
        """
        pass

    @abstractmethod
    def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
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
        self,
        customer_id: str,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
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

    # Payment Methods
    @abstractmethod
    def attach_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Returns:
            Dict with keys: id, customer_id, type, card/bank details
        """
        pass

    @abstractmethod
    def detach_payment_method(self, payment_method_id: str) -> Dict[str, Any]:
        """
        Detach a payment method from a customer.
        
        Returns:
            Dict with keys: id, customer_id
        """
        pass

    @abstractmethod
    def list_payment_methods(
        self,
        customer_id: str,
        method_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List payment methods for a customer.
        
        Args:
            customer_id: The customer ID
            method_type: Optional type filter (card, bank_account, etc.)
            
        Returns:
            List of payment method dicts
        """
        pass

    @abstractmethod
    def set_default_payment_method(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Set the default payment method for a customer.
        
        Returns:
            Dict with updated customer data
        """
        pass

    # One-time Payments
    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for a one-time payment.
        
        Args:
            amount: Amount in the currency's smallest unit (e.g., cents)
            currency: Three-letter currency code (e.g., 'gbp', 'usd')
            
        Returns:
            Dict with keys: id, amount, currency, status, client_secret
        """
        pass

    @abstractmethod
    def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent.
        
        Returns:
            Dict with keys: id, status, amount, currency
        """
        pass

    @abstractmethod
    def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Retrieve payment intent details.
        
        Returns:
            Dict with keys: id, amount, currency, status
        """
        pass

    # Checkout Sessions (for hosted checkout pages)
    @abstractmethod
    def create_checkout_session(
        self,
        customer_id: Optional[str] = None,
        price_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        mode: str = 'subscription',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session for hosted payment page.
        
        Args:
            mode: 'subscription' or 'payment'
            
        Returns:
            Dict with keys: id, url, customer_id, mode
        """
        pass

    @abstractmethod
    def get_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve checkout session details.
        
        Returns:
            Dict with keys: id, customer_id, payment_status, mode
        """
        pass

    # Invoices
    @abstractmethod
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Retrieve invoice details.
        
        Returns:
            Dict with keys: id, customer_id, amount_due, amount_paid, status
        """
        pass

    @abstractmethod
    def list_invoices(
        self,
        customer_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List invoices for a customer.
        
        Returns:
            List of invoice dicts
        """
        pass

    # Webhooks
    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> Dict[str, Any]:
        """
        Verify and parse a webhook payload.
        
        Returns:
            Dict with keys: type, data (the event object)
        """
        pass
