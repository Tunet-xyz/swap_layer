"""
Geolocation service using Azure Maps API.
"""

import logging
import requests

from typing import Optional



from .countries import (
    DEFAULT_CONFIG,
    LOCAL_DEV_CONFIG,
    get_country_config,
)

logger = logging.getLogger(__name__)


class GeolocationService:
    """
    Service for IP-based geolocation using Azure Maps.
    
    Usage:
        service = GeolocationService(subscription_key="your-key")
        result = service.get_location(request)
    """
    
    API_URL = "https://atlas.microsoft.com/geolocation/ip/json"
    API_VERSION = "1.0"
    
    def __init__(
        self,
        subscription_key: str,
        default_config: Optional[dict] = None,
        local_dev_config: Optional[dict] = None,
    ):
        """
        Initialize the geolocation service.
        
        Args:
            subscription_key: Azure Maps subscription key
            default_config: Fallback config for unsupported countries
            local_dev_config: Config to use for localhost/development
        """
        self.subscription_key = subscription_key
        self.default_config = default_config or DEFAULT_CONFIG
        self.local_dev_config = local_dev_config or LOCAL_DEV_CONFIG
    
    def _extract_ip_address(self, request) -> str:
        """Extract client IP address from Django request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _is_local_ip(self, ip_address: str) -> bool:
        """Check if IP address is localhost."""
        return ip_address in ('127.0.0.1', '::1', 'localhost')
    
    def get_location(self, request) -> dict:
        """
        Get geolocation info for the client making the request.
        
        Args:
            request: Django HTTP request object
            
        Returns:
            Dict with 'jurisdiction' and 'language' keys
        """
        ip_address = self._extract_ip_address(request)
        
        if self._is_local_ip(ip_address):
            return self.local_dev_config.copy()
        
        return self._fetch_location(ip_address)
    
    def get_location_by_ip(self, ip_address: str) -> dict:
        """
        Get geolocation info for a specific IP address.
        
        Args:
            ip_address: IP address to lookup
            
        Returns:
            Dict with 'jurisdiction' and 'language' keys
        """
        if self._is_local_ip(ip_address):
            return self.local_dev_config.copy()
        
        return self._fetch_location(ip_address)
    
    def _fetch_location(self, ip_address: str) -> dict:
        """Fetch location from Azure Maps API."""
        params = {
            'api-version': self.API_VERSION,
            'ip': ip_address,
            'subscription-key': self.subscription_key,
        }
        
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                iso_code = data.get('countryRegion', {}).get('isoCode')
                
                if iso_code:
                    return get_country_config(iso_code)
                
                logger.warning(f"No ISO code in response for IP {ip_address}")
                return self.default_config.copy()
            
            logger.error(f"Azure Maps API error: {response.status_code} - {response.text}")
            return self.default_config.copy()
            
        except requests.Timeout:
            logger.error(f"Azure Maps API timeout for IP {ip_address}")
            return self.default_config.copy()
        except requests.RequestException as e:
            logger.error(f"Azure Maps API request failed: {e}")
            return self.default_config.copy()

