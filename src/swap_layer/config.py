import os
from typing import Any, Optional

class Settings:
    """
    A framework-agnostic settings wrapper.
    Prioritizes Framework settings (like Django) if available.
    Falls back to environment variables.
    """
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        1. Try Django settings (dynamically checked on every access)
        2. Try Environment variables
        3. Return default
        """
        # 1. Django (if FRAMEWORK is explicitly 'django' or detected)
        # We can optionally control this via a FRAMEWORK env var, 
        # but the try/except block handles auto-detection well.
        
        try:
            from django.conf import settings as django_settings
            if django_settings.configured and hasattr(django_settings, key):
                return getattr(django_settings, key)
        except ImportError:
            pass
            
        # 2. Environment
        return os.environ.get(key, default)

    def getattr(self, key: str, default: Any = None) -> Any:
        """Alias for get to mimic some Django usage patterns if needed"""
        return self.get(key, default)
    
    def __getattr__(self, name: str) -> Any:
        # Enable usage like settings.SOME_KEY
        val = self.get(name)
        if val is None:
            # Check if user provided a default via get(), otherwise raise error
            # But since __getattr__ is only called if attribute is missing...
            # We mimic Django's behavior: strict access raises, safe access via getattr() returns None/default.
             raise AttributeError(f"Setting '{name}' not found.")
        return val

settings = Settings()
