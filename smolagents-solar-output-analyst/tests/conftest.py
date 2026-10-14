import pytest

from solar_analyst.data import load_production


@pytest.fixture(scope="session")
def df():
    return load_production()
