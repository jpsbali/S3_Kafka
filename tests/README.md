# Test Suite for CSV to Kafka Processor

## Overview

This directory contains comprehensive tests for the CSV to Kafka processor, including unit tests, integration tests, and performance tests.

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, no external dependencies)
│   ├── test_checkpoint_manager.py  # CheckpointManager tests
│   ├── test_metrics_emitter.py     # MetricsEmitter tests
│   └── test_csv_processor.py       # CSVToKafkaProcessor tests (TODO)
├── integration/                    # Integration tests (require AWS/Kafka)
│   ├── test_s3_integration.py      # S3 integration tests (TODO)
│   ├── test_dynamodb_integration.py # DynamoDB integration tests (TODO)
│   └── test_kafka_integration.py   # Kafka integration tests (TODO)
├── performance/                    # Performance tests
│   └── test_throughput.py          # Throughput tests (TODO)
├── fixtures/                       # Test data
│   └── sample_data.csv             # Sample CSV files (TODO)
├── conftest.py                     # Pytest configuration
├── requirements-test.txt           # Test dependencies
└── README.md                       # This file
```

## Setup

### 1. Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

### 2. Install Application Dependencies

```bash
pip install -r option1-ecs-fargate/app/requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Unit Tests Only

```bash
pytest tests/unit/
```

### Run with Coverage

```bash
pytest --cov=processor --cov-report=html tests/unit/
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Run Specific Test File

```bash
pytest tests/unit/test_checkpoint_manager.py
```

### Run Specific Test

```bash
pytest tests/unit/test_checkpoint_manager.py::TestCheckpointManager::test_update_checkpoint
```

### Run with Verbose Output

```bash
pytest -v tests/
```

### Run Tests Matching Pattern

```bash
pytest -k "checkpoint" tests/
```

## Test Markers

Tests are marked with custom markers for selective execution:

### Available Markers

- `@pytest.mark.integration` - Integration tests (require AWS services)
- `@pytest.mark.e2e` - End-to-end tests (require full stack)
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.kafka` - Tests requiring Kafka instance

### Run Tests by Marker

```bash
# Run only unit tests (no markers)
pytest tests/unit/

# Run integration tests
pytest -m integration tests/

# Run performance tests
pytest -m performance tests/

# Skip integration tests
pytest -m "not integration" tests/
```

## Test Coverage

### Current Coverage

| Component | Coverage | Status |
|-----------|----------|--------|
| CheckpointManager | 100% | ✅ Complete |
| MetricsEmitter | 100% | ✅ Complete |
| CSVToKafkaProcessor | 0% | ⏳ TODO |
| **Overall** | **~40%** | 🚧 In Progress |

### Coverage Goals

- CheckpointManager: 90%+ ✅
- MetricsEmitter: 85%+ ✅
- CSVToKafkaProcessor: 80%+ ⏳
- Overall: 80%+ ⏳

## Writing Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<what_it_tests>`

### Example Test

```python
import pytest
from unittest.mock import Mock, patch

class TestMyClass:
    
    @pytest.fixture
    def mock_dependency(self):
        """Setup mock dependency"""
        with patch('module.Dependency') as mock:
            yield mock
    
    def test_my_function(self, mock_dependency):
        """Test my function does X"""
        # Arrange
        mock_dependency.return_value = 'expected'
        
        # Act
        result = my_function()
        
        # Assert
        assert result == 'expected'
        mock_dependency.assert_called_once()
```

## Integration Tests

Integration tests require external services. Use LocalStack or moto for AWS services.

### Using Moto (AWS Mocking)

```python
from moto import mock_s3, mock_dynamodb
import boto3

@mock_s3
@mock_dynamodb
def test_with_aws():
    # Create mock S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    # Test code here
```

### Using Real Kafka (Optional)

For Kafka integration tests, start Kafka locally:

```bash
docker-compose up -d kafka
```

Then run Kafka tests:
```bash
pytest -m kafka tests/integration/
```

## Performance Tests

Performance tests measure throughput, latency, and resource usage.

### Run Performance Tests

```bash
pytest -m performance tests/performance/
```

### Performance Benchmarks

Expected performance:
- Throughput: > 10,000 records/sec
- Latency (p50): < 50ms
- Latency (p99): < 500ms
- Memory growth: < 100MB

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Nightly builds

### GitHub Actions

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Import Errors

If you get import errors:
```bash
# Make sure you're in the project root
cd /path/to/project

# Install in development mode
pip install -e option1-ecs-fargate/app/
```

### AWS Credential Errors

For moto tests, credentials are mocked automatically in `conftest.py`.

If you see credential errors:
```bash
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_DEFAULT_REGION=us-east-1
```

### Kafka Connection Errors

For Kafka tests, ensure Kafka is running:
```bash
docker-compose ps kafka
```

If not running:
```bash
docker-compose up -d kafka
```

## TODO

### Unit Tests
- [ ] Complete CSVToKafkaProcessor tests
- [ ] Add helper function tests
- [ ] Add error scenario tests

### Integration Tests
- [ ] S3 integration tests
- [ ] DynamoDB integration tests
- [ ] Kafka integration tests
- [ ] End-to-end workflow tests

### Performance Tests
- [ ] Throughput benchmarks
- [ ] Memory usage tests
- [ ] Latency measurements
- [ ] Load testing

### Infrastructure
- [ ] GitHub Actions workflow
- [ ] Coverage reporting
- [ ] Test data generation
- [ ] Docker compose for test services

## Contributing

When adding new tests:

1. Follow the naming convention
2. Add docstrings to test methods
3. Use fixtures for setup/teardown
4. Mock external dependencies
5. Aim for 80%+ coverage
6. Run tests before committing

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [moto documentation](https://docs.getmoto.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Plan](../TESTING_PLAN.md)

---

**Test Suite Version:** 1.0.0  
**Last Updated:** January 16, 2026
