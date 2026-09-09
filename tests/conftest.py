import pytest


def pytest_configure(config):
    """Register the 'network' marker to avoid unknown-marker warnings."""
    config.addinivalue_line(
        "markers",
        "network: test requires network access (run offline with `-m \"not network\"`)",
    )
