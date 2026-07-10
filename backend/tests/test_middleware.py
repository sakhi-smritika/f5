import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.middleware import RequestLoggingMiddleware


@pytest.fixture
def middleware_app():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/hello")
    def hello():
        return {"message": "hello"}

    @app.get("/client-error")
    def client_error():
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=404, content={"detail": "not found"})

    @app.get("/server-error")
    def server_error():
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content={"detail": "failed"})

    return app


@pytest.fixture
def middleware_client(middleware_app):
    with TestClient(middleware_app) as test_client:
        yield test_client


def test_health_path_is_not_request_logged(middleware_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = middleware_client.get("/health")

    assert response.status_code == 200
    assert not [record for record in caplog.records if record.name == "app.request"]


def test_successful_request_is_logged(middleware_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = middleware_client.get("/api/v1/hello")

    assert response.status_code == 200
    request_logs = [record for record in caplog.records if record.name == "app.request"]
    assert len(request_logs) == 1
    assert request_logs[0].message == "Request completed"
    assert request_logs[0].method == "GET"
    assert request_logs[0].path == "/api/v1/hello"
    assert request_logs[0].status_code == 200


def test_client_error_is_logged_as_warning(middleware_client, caplog):
    with caplog.at_level(logging.WARNING, logger="app.request"):
        response = middleware_client.get("/client-error")

    assert response.status_code == 404
    request_logs = [record for record in caplog.records if record.name == "app.request"]
    assert len(request_logs) == 1
    assert request_logs[0].levelname == "WARNING"
    assert request_logs[0].message == "Request completed with client error"


def test_server_error_is_logged_as_error(middleware_client, caplog):
    with caplog.at_level(logging.ERROR, logger="app.request"):
        response = middleware_client.get("/server-error")

    assert response.status_code == 500
    request_logs = [record for record in caplog.records if record.name == "app.request"]
    assert len(request_logs) == 1
    assert request_logs[0].levelname == "ERROR"
    assert request_logs[0].message == "Request failed"
