# Testing Guide for MUBI Plugin

This document provides comprehensive information about testing the MUBI plugin.

## Quick Start

### 1. Setup Test Environment

```bash
# Run the setup script
./setup_test_env.sh

# Or manually:
python3 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
```

> **Note**: The `venv/` directory is automatically excluded from git via `.gitignore`. Virtual environments should never be committed to version control.

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/ -m security        # Security tests
pytest tests/ -m stress          # Stress tests  
pytest tests/ -m integration     # Integration tests
pytest tests/ -m e2e             # End-to-end tests
pytest tests/ -m quality         # Quality framework tests

# Run with coverage
pytest tests/ --cov=resources/lib --cov-report=html
```

## Test Organization

### Test Suites

| Suite | Files | Count | Purpose |
|-------|-------|-------|---------|
| **Unit Tests** | `test_*.py` | 167 | Individual component testing |
| **Integration Tests** | `test_integration.py` | 12 | Component interaction testing |
| **End-to-End Tests** | `test_e2e.py` | 8 | Complete user journey testing |
| **Security Tests** | `test_security.py` | 12 | Security vulnerability testing |
| **Stress Tests** | `test_stress.py` | 7 | Performance and load testing |
| **Quality Framework** | `test_quality_framework.py` | 11 | Enterprise testing patterns |
| **Environment Tests** | `test_environment.py` | 7 | Environment validation and CI/CD testing |

**Total: 224 tests across all suites**

### Test Markers

Use pytest markers to run specific test categories:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests for component interaction  
- `@pytest.mark.e2e` - End-to-end tests for complete user journeys
- `@pytest.mark.security` - Security validation tests
- `@pytest.mark.stress` - Stress and performance tests
- `@pytest.mark.quality` - Quality framework and enterprise pattern tests
- `@pytest.mark.slow` - Slow running tests (>5 seconds)
- `@pytest.mark.network` - Tests that require network access
- `@pytest.mark.filesystem` - Tests that interact with the file system

## Test Categories

### Security Tests (`test_security.py`)

Validates protection against common vulnerabilities:

- **URL Validation**: XSS, SSRF, local network access prevention
- **Path Traversal**: Directory traversal attack prevention
- **XML Injection**: XML/XSS injection in NFO generation
- **Command Injection**: Shell injection in external processes
- **Input Sanitization**: Malicious input handling
- **Session Security**: Sensitive data protection

```bash
# Run security tests
pytest tests/ -m security -v
```

### Stress Tests (`test_stress.py`)

Tests application behavior under load:

- **Large Libraries**: 5,000+ film handling
- **Concurrent Operations**: 100+ simultaneous requests
- **Memory Pressure**: Memory leak detection
- **Rapid Operations**: 1,000+ rapid state changes
- **Error Recovery**: Resilience under failure conditions

```bash
# Run stress tests (requires psutil)
pytest tests/ -m stress -v
```

### Quality Framework (`test_quality_framework.py`)

Demonstrates enterprise-grade testing patterns:

- **Error Scenarios**: Comprehensive error handling
- **Boundary Conditions**: Edge case validation
- **State Consistency**: Object state integrity
- **Performance Requirements**: Speed and efficiency validation
- **Logging Patterns**: Proper logging integration

```bash
# Run quality framework tests
pytest tests/ -m quality -v
```

## Dependencies

### Required for All Tests
- `pytest>=7.0.0`
- `pytest-mock>=3.10.0`
- `coverage>=7.0.0`

### Required for Stress Tests
- `psutil>=5.9.0` - Memory and process monitoring

### Development Tools
- `flake8>=6.0.0` - Code linting
- `black>=23.0.0` - Code formatting
- `isort>=5.12.0` - Import sorting

## Test Utilities

### Test Discovery Validation

```bash
python tests/test_discovery.py
```

Validates that all tests are properly discoverable and organized.

### Enterprise Test Runner

```bash
python tests/test_runner_enterprise.py
```

Comprehensive test runner with coverage analysis and reporting.

### Coverage Analysis

```bash
# Generate HTML coverage report
pytest tests/ --cov=resources/lib --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Continuous Integration

### GitHub Actions Integration

The test suite is fully integrated with GitHub Actions and runs automatically on pull requests and pushes to main branches.

**Current Workflow** (`.github/workflows/test.yml`):
- ✅ **Multi-Python Support**: Tests run on Python 3.8, 3.9, 3.10, and 3.11
- ✅ **Complete Dependencies**: All test dependencies including `psutil` are installed
- ✅ **Full Test Suite**: All 224 tests including stress tests run successfully
- ✅ **Coverage Reporting**: Automatic coverage reports with 65% minimum threshold
- ✅ **Codecov Integration**: Coverage data uploaded to Codecov for tracking

**Dependencies Installation**:
```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt  # Includes psutil for stress tests
```

**Test Execution**:
```yaml
- name: Run tests with pytest
  run: |
    pytest tests/ -v --tb=short --strict-markers

- name: Generate test coverage report
  run: |
    pytest tests/ --cov=resources --cov-config=.coveragerc --cov-report=xml --cov-report=html --cov-report=term-missing --cov-fail-under=65
```

### Test Selection for CI

- **Fast CI**: Unit + Integration tests (~30 seconds)
  ```bash
  pytest tests/ -m "not stress and not slow"
  ```
- **Full CI**: All tests including stress tests (~8 minutes)
  ```bash
  pytest tests/ -v
  ```
- **Security CI**: Security tests only (~1 minute)
  ```bash
  pytest tests/ -m security
  ```
- **Stress CI**: Stress tests only (~8 minutes)
  ```bash
  pytest tests/ -m stress
  ```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'psutil'**
   ```bash
   ./venv/bin/pip install psutil
   ```

2. **Test discovery fails**
   ```bash
   python tests/test_discovery.py
   ```

3. **Virtual environment issues**
   ```bash
   rm -rf venv
   ./setup_test_env.sh
   ```

### Performance Issues

- Use `-x` flag to stop on first failure
- Use `--lf` to run only last failed tests
- Use specific markers to run subset of tests

## Contributing

When adding new tests:

1. Follow existing naming conventions (`test_*.py`)
2. Add appropriate markers (`@pytest.mark.security`, etc.)
3. Include docstrings explaining test purpose
4. Update this documentation if adding new test categories

## Test Quality Standards

- **Coverage**: Maintain >90% code coverage
- **Performance**: Unit tests <1s, Integration tests <5s
- **Reliability**: Tests must be deterministic and repeatable
- **Documentation**: All test purposes clearly documented
- **Security**: All security fixes must have corresponding tests
