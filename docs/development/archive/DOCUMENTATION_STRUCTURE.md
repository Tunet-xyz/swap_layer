# SwapLayer Documentation Structure

This document defines the standardized documentation structure for all SwapLayer modules.

## Documentation Standards

Each module follows a **strict 3-file maximum** structure:

| File | Required | Purpose |
|------|----------|---------|
| **README.md** | ✅ Always | Complete API reference, configuration, examples |
| **GUIDE.md** | 📝 Optional | Quick-start guide, migration examples, common patterns |
| **DECISIONS.md** | 📝 Optional | Architectural decisions, trade-offs, historical context |

**NO OTHER `.md` FILES ALLOWED IN MODULE DIRECTORIES**

---

## Current Structure

### ✅ Root Level
```
swap_layer/
├── README.md                    # Project overview and installation
└── ABSTRACTIONS_OVERVIEW.md     # Cross-module architecture guide
```

### ✅ Email Module
```
src/swap_layer/email/
├── README.md                    # Complete API reference (463 lines)
└── GUIDE.md                     # Quick-start & migration guide (NEW)
```

### ✅ Payments Module
```
src/swap_layer/payments/
├── README.md                    # Complete API reference (416 lines)
└── GUIDE.md                     # Migration from direct Stripe usage
```

### ✅ SMS Module
```
src/swap_layer/sms/
└── README.md                    # Complete API reference (534 lines)
```

### ✅ Storage Module
```
src/swap_layer/storage/
└── README.md                    # Complete API reference (447 lines)
```

### ✅ Identity Platform Module
```
src/swap_layer/identity/platform/
├── README.md                    # Complete API reference (NEW - 360 lines)
└── DECISIONS.md                 # Architectural decisions (renamed from DECISION_RECORD.md)
```

### ✅ Identity Verification Module
```
src/swap_layer/identity/verification/
└── README.md                    # Complete API reference (REWRITTEN - 250 lines)
```

---

## Deleted Files (Cleanup Complete)

The following redundant/outdated files were removed:

❌ `src/swap_layer/email/EMAIL_ABSTRACTION_SUMMARY.md` - Redundant summary  
❌ `src/swap_layer/email/ARCHITECTURE_COMPARISON.md` - Outdated comparison  
❌ `src/swap_layer/payments/ARCHITECTURE_COMPARISON.md` - Redundant comparison  
❌ `CODEBASE_AUDIT_REPORT.md` - Temporary audit document

---

## README.md Template

Every module's `README.md` follows this structure:

```markdown
# Module Name

[One-line description]

## Overview
[Problem statement and solution]

## Architecture
[Directory tree visualization]

## Features
[Bulleted list]

## Configuration
[Django settings example]

## Usage Examples
[Progressive examples: basic → advanced]

## Provider Comparison
[Feature matrix table]

## Normalized Data Format
[JSON schema examples]

## Benefits
[Numbered list]

## Adding a New Provider
[Step-by-step guide]

## Testing
[Mock examples]

## Related Modules
[Cross-references]

## License
```

---

## GUIDE.md Template

Migration and quick-start guides follow this structure:

```markdown
# Module Name - Quick Start Guide

## Why Use the Abstraction?

**Before** (Direct usage - vendor lock-in):
[Code example]

**After** (Provider-agnostic - swap anytime):
[Code example]

✅ Benefits list

---

## Quick Migration Examples

### 1. Feature Name
**Before:**
[Old code]

**After:**
[New code]

[More examples...]

---

## Common Patterns

[Real-world usage patterns]

---

## Testing Your Code

[Mock examples]

---

## Provider Comparison

[Quick comparison table]

---

## Configuration

[Settings examples per provider]

---

## Troubleshooting

[Common errors and solutions]

---

## Next Steps

[Actionable checklist]
```

---

## DECISIONS.md Template

Architectural decision records follow this structure:

```markdown
# Module Name - Architectural Decisions

## Decision 1: [Title]

**Date:** YYYY-MM-DD  
**Status:** Accepted | Deprecated | Superseded

### Context
[Why was this decision needed?]

### Decision
[What was decided?]

### Consequences
**Positive:**
- [Benefit 1]

**Negative:**
- [Trade-off 1]

**Neutral:**
- [Implementation detail]

---

[More decisions...]
```

---

## Enforcement

To add new documentation:

1. ✅ **Is it API reference?** → Update `README.md`
2. ✅ **Is it a how-to/migration?** → Update `GUIDE.md`
3. ✅ **Is it an architectural decision?** → Update `DECISIONS.md`
4. ❌ **New file?** → **NO.** Consolidate into existing files.

---

## Validation Checklist

Before committing documentation:

- [ ] Module has `README.md` with complete API reference
- [ ] No redundant `.md` files in module directory
- [ ] `GUIDE.md` exists only if there are migration/quickstart needs
- [ ] `DECISIONS.md` exists only if there are architectural decisions to document
- [ ] All cross-references use correct `swap_layer.*` package names
- [ ] Code examples are tested and working

---

## Summary Statistics

| Module | README | GUIDE | DECISIONS | Status |
|--------|--------|-------|-----------|--------|
| **email** | ✅ 463 lines | ✅ NEW | - | Complete |
| **payments** | ✅ 416 lines | ✅ 604 lines | - | Complete |
| **sms** | ✅ 534 lines | - | - | Complete |
| **storage** | ✅ 447 lines | - | - | Complete |
| **identity/platform** | ✅ 360 lines | - | ✅ Renamed | Complete |
| **identity/verification** | ✅ 250 lines | - | - | Complete |

**Total Documentation:** 6 modules, 9 files, ~2,500 lines of high-quality docs

---

**Last Updated:** January 6, 2026  
**Maintained By:** SwapLayer Core Team
