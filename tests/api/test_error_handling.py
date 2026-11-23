"""Checks the two-path error system with a tiny app (no Mongo/Redis/MinIO needed)."""
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.platform.shared.errors import Conflict, ServiceUnavailable
from app.platform.shared.handlers import register_error_handlers
from app.platform.shared.middleware import RequestContextMiddleware


class Body(BaseModel):
    n: int


def make_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    @app.get("/conflict")
    async def conflict():
        raise Conflict("internal detail: row locked", public_message="Already done.")

    @app.get("/infra")
    async def infra():
        raise ServiceUnavailable("mongo timeout at 10.0.0.5:27017")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret stack detail")

    @app.post("/validate")
    async def validate(body: Body):
        return body

    return TestClient(app, raise_server_exceptions=False)


def test_client_sees_safe_message_and_request_id(caplog):
    client = make_client()
    with caplog.at_level(logging.WARNING):
        r = client.get("/conflict", headers={"X-Request-ID": "abc-123"})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "conflict" and err["message"] == "Already done."
    assert err["request_id"] == "abc-123"
    assert "row locked" not in r.text            # path 2: nothing internal leaks
    assert "row locked" in caplog.text           # path 1: but our logs have it


def test_infrastructure_details_never_reach_the_client():
    r = make_client().get("/infra")
    assert r.status_code == 503
    assert "10.0.0.5" not in r.text


def test_unhandled_exception_becomes_generic_500():
    r = make_client().get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret stack detail" not in r.text


def test_validation_errors_are_listed_per_field():
    r = make_client().post("/validate", json={"n": "not-a-number"})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_error"
    assert body["details"][0]["field"] == "n"


def test_unknown_route_uses_the_same_envelope():
    r = make_client().get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "http_404"
