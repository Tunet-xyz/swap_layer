import os
from typing import Any, Optional

class Settings:
    """
    A framework-agnostic settings wrapper.
    Prioritizes Framework settings (like Django) if available.
    Falls back to environment variables.
    """
    
    def __init__(self):
        self._django_settings = None
        self._configured = False
        
        # Try to initialize Django settings
        try:
            from django.conf import settings
            # We check if settings are actually configured to avoid errors 
            # when Django is installed but not used in this context
            if settings.configured:
                self._django_settings = settings
        except ImportError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        1. Try Django settings
        2. Try Environment variables
        3. Return default
        """
        # 1. Django
        if self._django_settings and hasattr(self._django_settings, key):
            return getattr(self._django_settings, key)
            
        # 2. Environment
        return os.environ.get(key, default)

    def getattr(self, key: str, default: Any = None) -> Any:
        """Alias for get to mimic some Django usage patterns if needed"""
        return self.get(key, default)
    
    def __getattr__(self, name: str) -> Any:
        # Enable usage like settings.SOME_KEY
        val = self.get(name)
        if val is None:
             raise AttributeError(f"Setting '{name}' not found.")
        return val

settings = Settings()
