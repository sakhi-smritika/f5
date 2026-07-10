from fastapi import FastAPI


def test_create_app_returns_fastapi_instance(app):
    assert isinstance(app, FastAPI)
    assert app.title == "My FastAPI Application"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello_endpoint(client):
    response = client.get("/api/v1/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "hello"}


def test_unhandled_exception_returns_500(app):
    @app.get("/test-boom")
    def boom():
        raise RuntimeError("boom")

    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_main_module_exposes_app(reset_logging):
    import main

    assert isinstance(main.app, FastAPI)
