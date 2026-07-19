"""Pytest configuration and shared fixtures."""

import os

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.llm import MockLLMProvider


@pytest.fixture
def app(tmp_path):
    os.environ["CAREFLOW_ENVIRONMENT"] = "testing"
    os.environ["CAREFLOW_DATABASE_URL"] = f"sqlite:///{tmp_path}/api_test.db"
    # engine/session factory are lazy module singletons — reset per test app
    from app.infrastructure.database import reset_state

    reset_state()
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    # context manager triggers the lifespan (startup schema creation)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_llm_provider():
    return MockLLMProvider()
