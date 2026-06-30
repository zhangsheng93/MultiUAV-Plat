import logging

import pytest
import requests

from uav_api_client import UAVAPIClient


class FakeResponse:
    def __init__(self, payload=None, status_code=200, http_error=None):
        self.payload = payload if payload is not None else {"ok": True}
        self.status_code = status_code
        self.http_error = http_error

    def raise_for_status(self):
        if self.http_error:
            self.http_error.response = self
            raise self.http_error

    def json(self):
        return self.payload


def test_move_to_logs_command_endpoint_and_params(monkeypatch, caplog):
    captured = {}

    def fake_request(method, url, headers=None, **kwargs):
        captured.update({"method": method, "url": url, "headers": headers, "kwargs": kwargs})
        return FakeResponse({"success": True})

    monkeypatch.setattr(requests, "request", fake_request)
    caplog.set_level(logging.INFO, logger="uav_api_client")

    result = UAVAPIClient("http://multi-uav.test").move_to("drone-1", 10, 20, 15)

    assert result == {"success": True}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://multi-uav.test/drones/drone-1/command/move_to"
    assert captured["kwargs"]["params"] == {"x": 10, "y": 20, "z": 15}
    assert "MultiUAV-Plat request method=POST endpoint=/drones/drone-1/command/move_to" in caplog.text
    assert 'params={"x": 10, "y": 20, "z": 15}' in caplog.text
    assert "json=null" in caplog.text


def test_move_to_strips_null_path_result_fields(monkeypatch, caplog):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(
            {
                "success": True,
                "command": "move_to",
                "successful_points_count": None,
                "successful_points": None,
                "unsuccessful_points_count": None,
                "unsuccessful_points": None,
            }
        )

    monkeypatch.setattr(requests, "request", fake_request)
    caplog.set_level(logging.INFO, logger="uav_api_client")

    result = UAVAPIClient().move_to("drone-1", 10, 20, 15)

    assert result == {"success": True, "command": "move_to"}
    assert "successful_points" not in caplog.text
    assert "unsuccessful_points" not in caplog.text


def test_move_towards_strips_path_result_fields(monkeypatch, caplog):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(
            {
                "success": True,
                "command": "move_towards",
                "successful_points_count": 1,
                "successful_points": [{"x": 1, "y": 2, "z": 3}],
                "unsuccessful_points_count": 0,
                "unsuccessful_points": [],
            }
        )

    monkeypatch.setattr(requests, "request", fake_request)
    caplog.set_level(logging.INFO, logger="uav_api_client")

    result = UAVAPIClient().move_towards("drone-1", 10)

    assert result == {"success": True, "command": "move_towards"}
    assert "successful_points" not in caplog.text
    assert "unsuccessful_points" not in caplog.text


def test_move_along_path_logs_json_body(monkeypatch, caplog):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse({"success": True, "waypoint_count": 2})

    monkeypatch.setattr(requests, "request", fake_request)
    caplog.set_level(logging.INFO, logger="uav_api_client")

    result = UAVAPIClient().move_along_path(
        "drone-2",
        [{"x": 1.0, "y": 2.0, "z": 3.0}, {"x": 4.0, "y": 5.0, "z": 6.0}],
        allow_partial_move=False,
    )

    assert result == {"success": True, "waypoint_count": 2}
    assert "endpoint=/drones/drone-2/command/move_along_path" in caplog.text
    assert '"allow_partial_move": false' in caplog.text
    assert '"waypoints": [{"x": 1.0, "y": 2.0, "z": 3.0}, {"x": 4.0, "y": 5.0, "z": 6.0}]' in caplog.text


def test_request_logging_excludes_headers_and_api_key(monkeypatch, caplog):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse({"success": True})

    monkeypatch.setattr(requests, "request", fake_request)
    caplog.set_level(logging.INFO, logger="uav_api_client")

    client = UAVAPIClient(api_key="system_secret_key_change_in_production")
    client._request(
        "POST",
        "/drones/drone-1/command/land",
        headers={"Authorization": "Bearer custom-secret"},
    )

    assert "X-API-Key" not in caplog.text
    assert "system_secret_key_change_in_production" not in caplog.text
    assert "Authorization" not in caplog.text
    assert "custom-secret" not in caplog.text


def test_api_call_recording_captures_sanitized_success(monkeypatch):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(
            {
                "success": True,
                "command": "move_to",
                "successful_points_count": None,
                "successful_points": None,
            }
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = UAVAPIClient(api_key="system_secret_key_change_in_production")
    client.start_api_call_recording()
    client.move_to("drone-1", 10, 20, 15)
    records = client.stop_api_call_recording()

    assert records == [
        {
            "index": 1,
            "started_at": records[0]["started_at"],
            "method": "POST",
            "endpoint": "/drones/drone-1/command/move_to",
            "params": {"x": 10, "y": 20, "z": 15},
            "json": None,
            "data": None,
            "success": True,
            "status_code": 200,
            "response": {"success": True, "command": "move_to"},
            "error": None,
            "completed_at": records[0]["completed_at"],
        }
    ]
    assert "system_secret_key_change_in_production" not in str(records)
    assert "successful_points" not in str(records)


def test_api_call_recording_captures_error(monkeypatch):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(
            {"detail": "SYSTEM role required"},
            status_code=403,
            http_error=requests.exceptions.HTTPError("403 Client Error"),
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = UAVAPIClient()
    client.start_api_call_recording()
    with pytest.raises(Exception, match="Permission denied: SYSTEM role required"):
        client.land("drone-1")
    records = client.stop_api_call_recording()

    assert records[0]["success"] is False
    assert records[0]["status_code"] == 403
    assert records[0]["response"] == {"detail": "SYSTEM role required"}
    assert records[0]["error"] == "Permission denied: SYSTEM role required"


def test_request_returns_none_for_no_content(monkeypatch):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(status_code=204)

    monkeypatch.setattr(requests, "request", fake_request)

    assert UAVAPIClient().land("drone-1") is None


def test_request_preserves_http_error_mapping(monkeypatch):
    def fake_request(method, url, headers=None, **kwargs):
        return FakeResponse(
            {"detail": "SYSTEM role required"},
            status_code=403,
            http_error=requests.exceptions.HTTPError("403 Client Error"),
        )

    monkeypatch.setattr(requests, "request", fake_request)

    with pytest.raises(Exception, match="Permission denied: SYSTEM role required"):
        UAVAPIClient().land("drone-1")


def test_request_preserves_request_exception_mapping(monkeypatch):
    def fake_request(method, url, headers=None, **kwargs):
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "request", fake_request)

    with pytest.raises(Exception, match="API request failed: connection refused"):
        UAVAPIClient().land("drone-1")
