"""Shared pytest configuration for backend tests."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "anyio: mark test as async using anyio")
