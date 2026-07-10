import logging

import pytest

import config.logger as logger_module
from config.auth import AuthenticatedUser, get_current_user


@pytest.fixture
def reset_logging(monkeypatch, tmp_path):
    monkeypatch.setattr(logger_module, "_logging_configured", False)
    monkeypatch.setattr(logger_module, "LOGS_DIR", tmp_path)
    monkeypatch.setattr(logger_module, "LOG_FILEPATH", tmp_path / "test.log")

    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    yield

    root_logger.handlers.clear()
    monkeypatch.setattr(logger_module, "_logging_configured", False)


@pytest.fixture
def authenticated_user():
    return AuthenticatedUser(
        id="test-user-id",
        email="test@example.com",
        raw={"id": "test-user-id", "email": "test@example.com"},
    )


@pytest.fixture
def app(reset_logging, authenticated_user):
    from app import create_app

    application = create_app()
    application.dependency_overrides[get_current_user] = lambda: authenticated_user
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def unauthenticated_client(reset_logging):
    from app import create_app
    from fastapi.testclient import TestClient

    application = create_app()
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client
