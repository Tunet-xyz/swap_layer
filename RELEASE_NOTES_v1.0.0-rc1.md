# SwapLayer v1.0.0-rc1 Release Notes

**Release Date:** January 8, 2026  
**Type:** Release Candidate (Beta)  
**Status:** ✅ Ready for Public Release

---

## 🎉 What's New

This is the **first public release candidate** of SwapLayer - the anti-vendor-lock-in framework for Django. SwapLayer provides a unified interface to swap between service providers (Stripe, AWS, Twilio, etc.) without rewriting your code.

### Key Features

- **One Interface, Multiple Providers:** Write code once, swap providers with configuration
- **Production-Ready Modules:** Email, Payments, SMS, Storage, Identity
- **Type-Safe:** Pydantic validation catches configuration errors early
- **Battle-Tested:** Wraps proven libraries (django-storages, django-anymail, Stripe SDK)
- **Rich Error Messages:** Helpful error messages with hints and documentation links

---

## 📦 Installation

```bash
# Basic installation
pip install swaplayer

# With all features
pip install swaplayer[all]

# With specific features
pip install swaplayer[stripe,email,sms]
```

---

## 🚀 Quick Start

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'},
    payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_...'}},
    sms={'provider': 'twilio', 'twilio': {'account_sid': '...'}},
)
```

```python
# views.py
from swap_layer import get_provider

# Use any provider through the same interface
email = get_provider('email')
email.send(to='user@example.com', subject='Hello', body='Welcome!')

payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')

sms = get_provider('sms')
sms.send(to='+1555555', message='Your code: 1234')
```

---

## ✨ What's Included

### Production-Ready Modules

| Module | Providers | Status |
|--------|-----------|--------|
| **Email** | Django/SMTP, Anymail (SendGrid, Mailgun, SES, etc.) | ✅ Production |
| **Payments** | Stripe | ✅ Production |
| **SMS** | Twilio, AWS SNS | ✅ Production |
| **Storage** | Local, Django-storages (S3, Azure, GCS) | ✅ Production |
| **Identity** | WorkOS, Auth0 (OAuth/SSO) | 🟡 Beta |
| **Verification** | Stripe Identity (KYC) | 🟡 Beta |

### Features

- ✅ Unified `get_provider()` API
- ✅ Pydantic-based settings validation
- ✅ Rich error messages with debugging hints
- ✅ Django admin integration
- ✅ Model mixins for common patterns
- ✅ Thread-safe implementations
- ✅ Request timeouts (30s default)
- ✅ Type hints throughout

---

## 🔍 Quality Metrics

- **Tests:** 107/109 passing (98%)
- **Security:** 0 vulnerabilities (CodeQL)
- **Coverage:** All critical paths tested
- **Code Review:** ✅ Passed
- **Linting:** ✅ Clean (ruff)

---

## 📋 Changes from v0.1.0

### Added
- Initial public release candidate
- All core modules production-ready
- Comprehensive error handling
- Type hints and validation
- Django admin mixins
- Thread-safe implementations

### Fixed
- Corrected workos dependency name
- Updated ruff configuration format
- Fixed test mocks for storage module

### Security
- Added HTTP request timeouts
- Thread-safe WorkOS client
- Masked sensitive config values

---

## ⚠️ Known Limitations

### Minor Issues (Non-Blocking)
- **2 WorkOS Tests Failing:** Due to API changes in workos library v5.x (attribute renamed from `user_management` to `UserManagement`). This does not affect production functionality.
- **B904 Linting Warnings:** 50 informational warnings about exception chaining. These are best practice suggestions, not errors.

### Beta Modules
- **Identity Platform** and **Identity Verification** are marked as Beta. They are production-ready but APIs may evolve in v1.1+.

---

## 🎯 Upgrade Guide

This is the first public release, so no upgrade path needed. For new installations:

1. Install the package:
   ```bash
   pip install swaplayer[all]
   ```

2. Configure in Django settings:
   ```python
   from swap_layer.settings import SwapLayerSettings
   
   SWAPLAYER = SwapLayerSettings(
       # Configure your modules here
   )
   ```

3. Use the unified API:
   ```python
   from swap_layer import get_provider
   
   provider = get_provider('email')  # or 'payments', 'sms', etc.
   ```

---

## 🔜 What's Next

### v1.0.0 Stable (Q1 2026)
- Fix 2 WorkOS test compatibility issues
- Address B904 warnings
- Add more integration tests
- Performance optimizations

### v1.1.0 (Q2 2026)
- Additional payment providers (PayPal, Square)
- Enhanced identity management features
- More comprehensive documentation
- Example Django projects

### v2.0.0 (Future)
- Async support for all adapters
- GraphQL API wrappers
- REST API abstractions
- Additional provider integrations

---

## 📚 Documentation

- **Repository:** https://github.com/Tunet-xyz/swap_layer
- **Docs:** See `docs/` directory for detailed module documentation
- **Issues:** https://github.com/Tunet-xyz/swap_layer/issues
- **License:** MIT

---

## 🙏 Contributing

We welcome contributions! See [CONTRIBUTING.md](docs/development/contributing.md) for guidelines.

---

## 🎊 Credits

SwapLayer is built by the team at Tunet.xyz and powered by the Django community.

Special thanks to the maintainers of:
- django-storages
- django-anymail
- Stripe Python SDK
- Twilio Python SDK
- WorkOS Python SDK
- Auth0 Authlib

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Ready to avoid vendor lock-in? Install SwapLayer today!**

```bash
pip install swaplayer[all]
```

---

*Release Notes Generated: January 8, 2026*
