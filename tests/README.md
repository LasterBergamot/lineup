# Test Structure

This directory contains tests organized according to the **testing pyramid** principle.

## Testing Pyramid

```
        /\
       /E2E\        ← Few E2E tests (slow, comprehensive)
      /------\
     /Integration\  ← Some integration tests (medium speed)
    /------------\
   /    Unit      \ ← Many unit tests (fast, isolated)
  /----------------\
```

## Directory Structure

### `unit/` - Unit Tests
- **Purpose**: Test individual functions, methods, and classes in isolation
- **Characteristics**: Fast, isolated, no external dependencies
- **Examples**: Testing configuration classes, utility functions, data models

**Run unit tests only:**
```bash
poetry run pytest tests/unit/
```

### `integration/` - Integration Tests
- **Purpose**: Test how multiple components work together
- **Characteristics**: Medium speed, may involve database/API interactions
- **Examples**: Testing API endpoints, component interactions, Flask app factory

**Run integration tests only:**
```bash
poetry run pytest tests/integration/
```

### `e2e/` - End-to-End Tests
- **Purpose**: Test complete user scenarios from start to finish
- **Characteristics**: Slower, test the entire system
- **Examples**: Complete API flows, user journeys, system-wide scenarios

**Run E2E tests only:**
```bash
poetry run pytest tests/e2e/
```

## Shared Fixtures

The `conftest.py` file contains shared fixtures available to all tests:
- `app`: Application instance for testing
- `client`: Test client for making HTTP requests
- `runner`: CLI test runner

## Running Tests

**Run all tests:**
```bash
poetry run pytest
```

**Run with verbose output:**
```bash
poetry run pytest -v
```

**Run specific test level:**
```bash
poetry run pytest tests/unit/          # Unit tests only
poetry run pytest tests/integration/   # Integration tests only
poetry run pytest tests/e2e/          # E2E tests only
```

**Run with coverage:**
```bash
poetry run pytest --cov=app --cov=config --cov-report=html
```

This generates an HTML coverage report in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view it.

**Coverage report formats:**
- **Terminal output with missing lines**: `--cov-report=term-missing`
- **HTML report**: `--cov-report=html` (generates `htmlcov/index.html`)
- **XML report**: `--cov-report=xml` (generates `coverage.xml`, useful for CI/CD)

**Run specific test file:**
```bash
poetry run pytest tests/unit/test_config.py
```

**Run tests matching a pattern:**
```bash
poetry run pytest -k health          # Run all tests with "health" in the name
poetry run pytest -k "test_config"   # Run all tests with "test_config" in the name
```

## Test Organization Principles

1. **Unit tests** should be fast and test one thing at a time
2. **Integration tests** verify components work together correctly
3. **E2E tests** simulate real user scenarios
4. Use fixtures from `conftest.py` to avoid code duplication
5. Follow the naming convention: `test_*.py` for test files, `test_*` for test functions
