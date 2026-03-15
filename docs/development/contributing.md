# Contributing to SwapLayer

Thank you for your interest in contributing to SwapLayer!

## Documentation Standards

To maintain a clean, navigable codebase, we enforce **strict documentation rules**:

### 📁 Root Directory
**ONLY** `README.md` belongs at the root level. All other documentation goes in `docs/`.

### 📚 Documentation Directory (`docs/`)

- **User-facing guides**: Architecture, configuration, tutorials
- **Archive**: Historical development notes and decisions

```
docs/
├── README.md                    # Documentation index
├── architecture.md              # Architecture guide
├── [module].md                  # Module-specific guides (email.md, billing.md, etc.)
└── development/                 # Development history and notes
```

### 📦 Module Documentation

Each module follows a **maximum 3-file rule**:

```
src/swap_layer/[module]/
├── README.md        # ✅ REQUIRED - Complete API reference
├── GUIDE.md         # 📝 OPTIONAL - Quick-start/migration guide
└── DECISIONS.md     # 📝 OPTIONAL - Architecture decisions
```

**Rules:**
1. ✅ Every module MUST have `README.md`
2. ✅ `GUIDE.md` for migration examples or quick-starts (optional)
3. ✅ `DECISIONS.md` for architectural context (optional)
4. ❌ NO other `.md` files in modules
5. ❌ NO subdomain-specific READMEs (cover in main module README)

### ✍️ README Content Structure

Every module README should include:

```markdown
# Module Name

## Overview
Brief description and purpose

## Installation
Provider-specific dependencies

## Configuration
Settings and examples

## Usage
Basic examples

## API Reference
Complete interface documentation

## Provider Support
Available providers and status

## Error Handling
Common errors and solutions
```

### 🚫 What NOT to Do

❌ **Don't** create markdown files at the root
❌ **Don't** create subdomain-specific READMEs
❌ **Don't** duplicate information across files
❌ **Don't** mix development notes with user documentation
❌ **Don't** create "STATUS.md" or "COMPLETE.md" files (use archive)

### ✅ What TO Do

✅ **Do** add user-facing guides to `docs/`
✅ **Do** archive development notes in `docs/archive/`
✅ **Do** keep module READMEs comprehensive but focused
✅ **Do** link between related documents
✅ **Do** update the docs index when adding guides

## Code Contributions

### Module Structure

Each module follows this pattern:

```
src/swap_layer/[module]/
├── __init__.py          # Public exports
├── adapter.py           # Abstract base class
├── factory.py           # Provider factory
├── models.py            # Django models (if needed)
├── admin.py             # Django admin (if needed)
├── apps.py              # Django app config
├── README.md            # Documentation
└── providers/           # Provider implementations
    ├── __init__.py      # Provider exports
    └── [provider].py    # Provider implementation
```

### Testing

- All new features require tests
- Run test suite: `pytest`
- Test specific module: `pytest tests/test_[module].py`
- Verify documentation: `python manage.py swaplayer_check`

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow documentation standards above
4. Write tests for new functionality
5. Update relevant READMEs
6. Ensure all tests pass
7. Submit pull request

### Commit Message Format

```
type(scope): Brief description

- Detailed change 1
- Detailed change 2

Closes #issue-number
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Questions?

- Check [Documentation Index](../README.md)
- Review [Architecture Guide](../architecture.md)
- Review [LLM Agent Use Cases](../llm-agents.md) for AI-assisted development
- Open an issue for clarification

---

**Remember**: Clean documentation = Happy developers! 🎉
