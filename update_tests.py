"""
Script to update all test files to use Django settings properly.
This replaces the old config.settings.get() pattern with Django's direct attribute access.
"""
import os
import re


def update_test_file(filepath):
    """Update a single test file to use Django settings."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace import
    content = content.replace(
        'from swap_layer.config import settings',
        'from django.conf import settings'
    )
    
    # Remove old settings.get patterns in patches (complex, needs manual review)
    # Flag these for manual fixing
    if "patch.object(settings, 'get'" in content or "patch('swap_layer.config.settings.get')" in content:
        print(f"⚠️  {filepath} - Contains settings.get() patches that need manual fixing")
    
    # Remove old TestConfigSettings class that tests the removed Settings class
    if 'TestConfigSettings' in content:
        print(f"⚠️  {filepath} - Contains TestConfigSettings that tests removed Settings class")
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated {filepath}")


def main():
    test_dir = 'c:/Users/alexc/Documents/Github/swap_layer/tests'
    
    for filename in os.listdir(test_dir):
        if filename.startswith('test_') and filename.endswith('.py'):
            filepath = os.path.join(test_dir, filename)
            update_test_file(filepath)
    
    print("\n=== Summary ===")
    print("All test files have been updated to import from django.conf.")
    print("Files with settings.get() patches need manual review and updates.")
    print("Consider removing TestConfigSettings class as it tests removed functionality.")


if __name__ == '__main__':
    main()
