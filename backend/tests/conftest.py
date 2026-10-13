import os
import pytest

# Set before test modules import the application. Missing cloud credentials must
# not prevent collecting offline tests; database tests opt in with monkeypatch.
os.environ['BUSINESS_DATA_SOURCE'] = 'demo'


@pytest.fixture(autouse=True)
def explicit_offline_business_data(monkeypatch):
    # Tests opt in to database mode individually; never use a developer's key.
    monkeypatch.setenv('BUSINESS_DATA_SOURCE', 'demo')
