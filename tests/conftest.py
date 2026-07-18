"""Pytest configuration and shared fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.llm import MockLLMProvider
from app.main import create_app


@pytest.fixture
def app():
    os.environ["CAREFLOW_ENVIRONMENT"] = "testing"
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider()
