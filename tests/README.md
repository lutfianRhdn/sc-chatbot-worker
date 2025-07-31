# Unit Tests for SC-Chatbot-Worker

This directory contains comprehensive unit tests for the supervisor and worker classes in the sc-chatbot-worker project.

## Test Structure

```
tests/
├── __init__.py                      # Test package initialization
├── test_supervisor.py               # Comprehensive supervisor tests
├── test_worker_base.py             # Worker base class tests
├── test_utils/
│   ├── __init__.py                 # Utils test package
│   └── test_utils.py               # Utility function tests
└── test_workers/
    ├── __init__.py                 # Workers test package
    ├── test_vector_worker.py       # VectorWorker tests
    └── test_database_worker.py     # DatabaseInteractionWorker tests
```

## Test Coverage

### Supervisor Class Tests (`test_supervisor.py`)
- ✅ Worker creation and management
- ✅ Health checking functionality
- ✅ Message routing between workers
- ✅ Error handling and worker recovery
- ✅ Pending message tracking and resending
- ✅ Worker termination and cleanup
- ✅ Process lifecycle management
- ✅ Multi-worker scenarios

### Worker Base Class Tests (`test_worker_base.py`)
- ✅ Abstract method enforcement
- ✅ Worker interface compliance
- ✅ Inheritance validation
- ✅ Multiple inheritance compatibility
- ✅ Async method requirements
- ✅ Class structure validation

### Utility Function Tests (`test_utils/test_utils.py`)
- ✅ Message handling functions
- ✅ Logging functionality
- ✅ Message conversion and validation
- ✅ Error handling in utilities
- ✅ JSON serialization/deserialization

### Concrete Worker Tests
- ✅ **VectorWorker** (`test_workers/test_vector_worker.py`)
  - Worker initialization and configuration
  - Vector operations (create, insert)
  - Text processing functions
  - Message processing and routing
  - Error handling and communication

- ✅ **DatabaseInteractionWorker** (`test_workers/test_database_worker.py`)
  - Database connection management
  - Message processing and routing
  - Busy state handling
  - Error handling and communication

## Running Tests

### Basic Test Execution
```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run specific test pattern
python run_tests.py --pattern "test_supervisor*"
```

### Coverage Analysis
```bash
# Run tests with coverage (requires 'coverage' package)
python run_tests.py --coverage

# Install coverage if needed
pip install coverage
```

### Test Validation
```bash
# List all available tests
python run_tests.py --list

# Validate test structure
python run_tests.py --validate
```

### Individual Test Files
```bash
# Run specific test file
python -m unittest tests.test_supervisor -v

# Run specific test class
python -m unittest tests.test_supervisor.TestSupervisor -v

# Run specific test method
python -m unittest tests.test_supervisor.TestSupervisor.test_create_worker_success -v
```

## Test Framework Features

### Comprehensive Mocking
- All external dependencies are mocked (MongoDB, Azure OpenAI, multiprocessing, etc.)
- No external services required for testing
- Isolated test execution

### Error Scenario Testing
- Connection failures
- Module import errors
- Worker health failures
- Message processing errors
- Resource exhaustion scenarios

### Edge Case Coverage
- Empty configurations
- Invalid parameters
- Malformed messages
- Concurrent operations
- Resource cleanup

### Performance Validation
- Message throughput testing
- Memory usage patterns
- Resource cleanup verification

## Test Design Principles

### 1. Independence
- Each test is completely independent
- No shared state between tests
- Proper setup and teardown

### 2. Comprehensive Coverage
- Positive and negative test cases
- Edge cases and boundary conditions
- Error handling scenarios

### 3. Realistic Scenarios
- Tests simulate real-world usage patterns
- Complex message flows
- Multi-worker interactions

### 4. Maintainability
- Clear test names and documentation
- Logical test organization
- Easy to extend and modify

## Adding New Tests

### For New Worker Classes
1. Create test file: `tests/test_workers/test_new_worker.py`
2. Follow existing patterns in `test_vector_worker.py`
3. Mock all external dependencies
4. Test initialization, message processing, and error handling

### For New Utility Functions
1. Add tests to `tests/test_utils/test_utils.py`
2. Test all function parameters and return values
3. Include error scenarios

### For Supervisor Extensions
1. Add tests to `tests/test_supervisor.py`
2. Test new functionality with proper mocking
3. Verify integration with existing features

## Dependencies

### Required for Testing
- Python 3.12+ (standard library unittest)
- unittest.mock (included in Python 3.3+)

### Optional for Enhanced Features
- `coverage` - For coverage analysis
- `pytest` - Alternative test runner (compatible)

## Best Practices

1. **Mock External Dependencies**: Always mock database connections, API calls, file operations
2. **Test Error Scenarios**: Include tests for failure cases and edge conditions
3. **Use Descriptive Names**: Test method names should clearly describe what is being tested
4. **Verify All Interactions**: Use assert statements to verify mock calls and return values
5. **Clean Setup/Teardown**: Ensure proper cleanup to prevent test interference

## Continuous Integration

These tests are designed to run in CI/CD environments:
- No external dependencies required
- Fast execution (< 30 seconds for full suite)
- Clear pass/fail status
- Detailed error reporting

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src` directory is in Python path
2. **Mock Issues**: Verify correct patch targets (use full module paths)
3. **Async Test Failures**: Use proper async test patterns with `asyncio.run()`

### Debug Mode
```bash
# Run single test with maximum verbosity
python -m unittest tests.test_supervisor.TestSupervisor.test_create_worker_success -v

# Use Python debugger
python -m pdb -m unittest tests.test_supervisor
```

This comprehensive test suite ensures the reliability and robustness of the sc-chatbot-worker system.