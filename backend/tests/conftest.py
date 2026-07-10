import logging

import pytest

import config.logger as logger_module


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
def app(reset_logging):
    from app import create_app

    return create_app()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
