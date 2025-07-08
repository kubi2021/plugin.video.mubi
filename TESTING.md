# Testing Guide for MUBI Plugin

This document provides comprehensive information about testing the MUBI plugin.

## Quick Start

### 1. Setup Test Environment

```bash
# Run the setup script
./setup_test_env.sh

# Or manually:
python3 -m venv venv
./venv/bin/pip install -r requirements-test.txt
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

**Total: 217 tests across all suites**

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

The test suite is designed for CI/CD integration:

```yaml
- name: Setup Test Environment
  run: |
    python -m venv venv
    ./venv/bin/pip install -r requirements-test.txt

- name: Run Tests
  run: |
    source venv/bin/activate
    pytest tests/ --cov=resources/lib --cov-report=xml

- name: Run Security Tests
  run: |
    source venv/bin/activate
    pytest tests/ -m security
```

### Test Selection for CI

- **Fast CI**: Unit + Integration tests (~30 seconds)
- **Full CI**: All tests including stress tests (~5 minutes)
- **Security CI**: Security tests only (~1 minute)

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
