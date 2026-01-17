"""
Pytest configuration and shared fixtures
"""
import pytest
import os

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires AWS services)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (requires full stack)"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "kafka: mark test as requiring Kafka instance"
    )

@pytest.fixture(scope="session", autouse=True)
def aws_credentials():
    """Mock AWS credentials for moto"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    yield
    
    # Cleanup
    for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 
                'AWS_SECURITY_TOKEN', 'AWS_SESSION_TOKEN']:
        os.environ.pop(key, None)

@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing"""
    return [
        {'id': '1', 'name': 'Alice', 'value': '100'},
        {'id': '2', 'name': 'Bob', 'value': '200'},
        {'id': '3', 'name': 'Charlie', 'value': '300'},
    ]
