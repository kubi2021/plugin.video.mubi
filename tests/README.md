# MUBI Kodi Plugin - Test Suite

This directory contains comprehensive tests for the MUBI Kodi plugin. The test suite covers all major components and functionality of the plugin.

## Test Structure

### Test Files

- `test_film.py` - Tests for the Film class including initialization, validation, and file operations
- `test_metadata.py` - Tests for the Metadata class including data handling and conversion
- `test_session_manager.py` - Tests for SessionManager including device ID generation and login/logout
- `test_navigation_handler.py` - Tests for NavigationHandler including menu building and user interactions
- `test_mubi.py` - Tests for the Mubi API class including authentication and data retrieval
- `test_migrations.py` - Tests for the migrations module including XML handling and first-run logic
- `test_playback.py` - Tests for the playback module including DRM license generation
- `test_addon.py` - Tests for the main addon entry point including parameter parsing and routing
- `test_library.py` - Tests for the Library class (existing tests)

### Configuration Files

- `conftest.py` - Pytest configuration with fixtures and mocks for Kodi environment
- `pytest.ini` - Pytest configuration settings
- `requirements-test.txt` - Test dependencies
- `run_tests.py` - Test runner script with various options
- `Makefile` - Convenient make targets for testing

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

Or use the make target:
```bash
make install
```

### Basic Test Execution

Run all tests:
```bash
pytest tests/
```

Or use make:
```bash
make test
```

### Test Options

#### Verbose Output
```bash
pytest tests/ -v
# or
make test-verbose
```

#### Coverage Report
```bash
pytest tests/ --cov=resources --cov=addon --cov-report=html --cov-report=term-missing
# or
make test-coverage
```

#### Parallel Execution
```bash
pytest tests/ -n auto
# or
make test-parallel
```

#### Specific Test File
```bash
pytest tests/test_film.py -v
# or
make test-film
```

#### Specific Test Function
```bash
pytest tests/ -k "test_film_initialization" -v
```

### Using the Test Runner Script

The `run_tests.py` script provides additional options:

```bash
# Install dependencies and run tests with coverage
python run_tests.py --install-deps --coverage

# Run tests with linting
python run_tests.py --lint --test

# Format code and run tests
python run_tests.py --format --test

# Run specific test file
python run_tests.py --test-file test_film.py

# Run tests in parallel
python run_tests.py --parallel 4
```

## Test Coverage

The test suite aims for comprehensive coverage of:

### Core Components
- **Film Class**: Object creation, validation, file operations, metadata handling
- **Metadata Class**: Data initialization, validation, dictionary conversion
- **Library Class**: Film management, local synchronization, file operations
- **SessionManager**: Device ID generation, authentication state, settings management
- **NavigationHandler**: Menu building, action routing, user interactions
- **Mubi API**: Authentication, data retrieval, error handling
- **Migrations**: XML handling, source management, first-run logic
- **Playback**: DRM license generation, stream configuration
- **Main Addon**: Parameter parsing, action routing, initialization

### Test Types
- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction
- **Error Handling**: Exception scenarios and edge cases
- **Mock Testing**: Kodi environment simulation

## Mocking Strategy

The test suite uses extensive mocking to simulate the Kodi environment:

### Kodi Modules
- `xbmc` - Core Kodi functionality
- `xbmcaddon` - Addon management
- `xbmcgui` - User interface components
- `xbmcplugin` - Plugin functionality
- `xbmcvfs` - Virtual file system

### External Dependencies
- `inputstreamhelper` - Stream helper
- `requests` - HTTP requests
- File system operations

### Fixtures
- `mock_addon` - Mock addon instance
- `mock_metadata` - Mock metadata object
- `sample_film_data` - Sample API response data
- `mock_film` - Mock Film instance
- `mock_library` - Mock Library instance
- `temp_directory` - Temporary directory for file tests

## Best Practices

### Writing Tests
1. Use descriptive test names that explain what is being tested
2. Follow the Arrange-Act-Assert pattern
3. Mock external dependencies appropriately
4. Test both success and failure scenarios
5. Include edge cases and boundary conditions

### Test Organization
1. Group related tests in classes
2. Use fixtures for common setup
3. Keep tests independent and isolated
4. Use appropriate test markers for categorization

### Assertions
1. Use specific assertions that clearly indicate what failed
2. Include helpful error messages
3. Test multiple aspects when appropriate
4. Verify mock calls and arguments

## Continuous Integration

The test suite includes automated GitHub Actions workflow for continuous integration:

### GitHub Actions Workflow

The repository includes `.github/workflows/test.yml` which automatically:

- **Triggers on**: Pull requests and pushes to main/master branches
- **Tests multiple Python versions**: 3.8, 3.9, 3.10, 3.11
- **Runs full test suite** with verbose output
- **Generates coverage reports** in XML and HTML formats
- **Uploads coverage to Codecov** for tracking

### Workflow Features

```yaml
# Automatic testing on PR/push
on:
  pull_request:
    branches: [ main, master ]
  push:
    branches: [ main, master ]

# Matrix testing across Python versions
strategy:
  matrix:
    python-version: [3.8, 3.9, '3.10', '3.11']

# Coverage reporting
pytest tests/ --cov=resources --cov-report=xml --cov-report=html
```

### Local CI Simulation

To run the same tests locally as CI:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with coverage (same as CI)
pytest tests/ -v --tb=short --cov=resources --cov-report=xml --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all Kodi modules are properly mocked in `conftest.py`
2. **Path Issues**: Use relative paths and proper fixtures for file operations
3. **Mock Conflicts**: Reset mocks between tests using the `reset_modules` fixture
4. **Async Issues**: Some Kodi operations may need special handling

### Debug Tips

1. Use `pytest -s` to see print statements
2. Use `pytest --pdb` to drop into debugger on failures
3. Check mock call history with `mock.call_args_list`
4. Use `pytest -v` for detailed test output

## Contributing

When adding new functionality:

1. Write tests for new features
2. Maintain or improve test coverage
3. Follow existing test patterns
4. Update this README if needed
5. Ensure all tests pass before submitting
