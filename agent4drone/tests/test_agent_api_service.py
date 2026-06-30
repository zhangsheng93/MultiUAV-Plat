from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent_api_service import (
    app,
    command_response_from_result,
    initialize_agent_from_settings,
    jobs,
    JobInfo,
    JobStatus,
)


def test_command_response_converts_intermediate_step_namespaces():
    result = command_response_from_result(
        {
            "success": True,
            "output": "done",
            "token_usage": {
                "prompt_tokens": 4,
                "completion_tokens": 6,
                "total_tokens": 10,
                "llm_calls": 1,
            },
            "intermediate_steps": [
                (
                    SimpleNamespace(
                        tool="get_status",
                        tool_input={"drone_id": "drone-1"},
                        log="Preparing tool call",
                        message_log=None,
                    ),
                    "ok",
                )
            ],
        }
    )

    assert result.intermediate_steps == [
        [
            {
                "tool": "get_status",
                "tool_input": {"drone_id": "drone-1"},
                "log": "Preparing tool call",
                "message_log": None,
            },
            "ok",
        ]
    ]
    assert result.token_usage is not None
    assert result.token_usage.total_tokens == 10


def test_get_job_status_serializes_completed_job_with_steps():
    job_id = "test-job"
    jobs[job_id] = JobInfo(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        created_at=datetime.now(),
        completed_at=datetime.now(),
        command="status",
        result=command_response_from_result(
            {
                "success": True,
                "output": "done",
                "token_usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 3,
                    "total_tokens": 5,
                    "llm_calls": 1,
                },
                "intermediate_steps": [
                    (SimpleNamespace(tool="get_status", tool_input={}, log="log"), "ok")
                ],
            }
        ),
    )

    try:
        response = TestClient(app).get(f"/agent/jobs/{job_id}")
    finally:
        jobs.pop(job_id, None)

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intermediate_steps"][0][0]["tool"] == "get_status"
    assert body["result"]["token_usage"] == {
        "prompt_tokens": 2,
        "completion_tokens": 3,
        "total_tokens": 5,
        "llm_calls": 1,
    }


def test_initialize_agent_reads_uav_connection_from_settings(monkeypatch):
    captured = {}

    def fake_load_llm_settings(settings_path):
        return {
            "selected_provider": "TestProvider",
            "uav_base_url": "http://settings-uav.test",
            "uav_api_key": "settings-uav-key",
            "provider_configs": {
                "TestProvider": {
                    "type": "openai-compatible",
                    "base_url": "https://llm.example/v1",
                    "default_model": "test-model",
                    "requires_api_key": True,
                    "api_key": "llm-key",
                }
            },
        }

    class FakeUAVControlAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("UAV_API_URL", raising=False)
    monkeypatch.delenv("UAV_API_KEY", raising=False)
    monkeypatch.setattr("agent_api_service.load_llm_settings", fake_load_llm_settings)
    monkeypatch.setattr("agent_api_service.UAVControlAgent", FakeUAVControlAgent)

    initialize_agent_from_settings()

    assert captured["base_url"] == "http://settings-uav.test"
    assert captured["uav_api_key"] == "settings-uav-key"
    assert captured["llm_provider"] == "openai-compatible"
    assert captured["llm_model"] == "test-model"
    assert captured["share_blackboard_by_session"] is False
    assert captured["toolchain_json_recording"] is False


def test_initialize_agent_reads_blackboard_sharing_from_settings(monkeypatch):
    captured = {}

    def fake_load_llm_settings(settings_path):
        return {
            "selected_provider": "TestProvider",
            "share_blackboard_by_session": True,
            "provider_configs": {
                "TestProvider": {
                    "type": "openai-compatible",
                    "base_url": "https://llm.example/v1",
                    "default_model": "test-model",
                    "requires_api_key": True,
                    "api_key": "llm-key",
                }
            },
        }

    class FakeUAVControlAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("UAV_API_URL", raising=False)
    monkeypatch.delenv("UAV_API_KEY", raising=False)
    monkeypatch.setattr("agent_api_service.load_llm_settings", fake_load_llm_settings)
    monkeypatch.setattr("agent_api_service.UAVControlAgent", FakeUAVControlAgent)

    initialize_agent_from_settings()

    assert captured["share_blackboard_by_session"] is True


def test_initialize_agent_parses_string_blackboard_sharing_setting(monkeypatch):
    captured = {}

    def fake_load_llm_settings(settings_path):
        return {
            "selected_provider": "TestProvider",
            "share_blackboard_by_session": "true",
            "provider_configs": {
                "TestProvider": {
                    "type": "openai-compatible",
                    "base_url": "https://llm.example/v1",
                    "default_model": "test-model",
                    "requires_api_key": True,
                    "api_key": "llm-key",
                }
            },
        }

    class FakeUAVControlAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("UAV_API_URL", raising=False)
    monkeypatch.delenv("UAV_API_KEY", raising=False)
    monkeypatch.setattr("agent_api_service.load_llm_settings", fake_load_llm_settings)
    monkeypatch.setattr("agent_api_service.UAVControlAgent", FakeUAVControlAgent)

    initialize_agent_from_settings()

    assert captured["share_blackboard_by_session"] is True


def test_initialize_agent_reads_toolchain_recording_from_settings(monkeypatch):
    captured = {}

    def fake_load_llm_settings(settings_path):
        return {
            "selected_provider": "TestProvider",
            "toolchain_json_recording": "true",
            "provider_configs": {
                "TestProvider": {
                    "type": "openai-compatible",
                    "base_url": "https://llm.example/v1",
                    "default_model": "test-model",
                    "requires_api_key": True,
                    "api_key": "llm-key",
                }
            },
        }

    class FakeUAVControlAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.delenv("UAV_API_URL", raising=False)
    monkeypatch.delenv("UAV_API_KEY", raising=False)
    monkeypatch.setattr("agent_api_service.load_llm_settings", fake_load_llm_settings)
    monkeypatch.setattr("agent_api_service.UAVControlAgent", FakeUAVControlAgent)

    initialize_agent_from_settings()

    assert captured["toolchain_json_recording"] is True


def test_initialize_agent_allows_uav_env_overrides(monkeypatch):
    captured = {}

    def fake_load_llm_settings(settings_path):
        return {
            "selected_provider": "Ollama",
            "uav_base_url": "http://settings-uav.test",
            "uav_api_key": "settings-uav-key",
            "provider_configs": {
                "Ollama": {
                    "type": "ollama",
                    "base_url": "http://localhost:11434",
                    "default_model": "llama2",
                    "requires_api_key": False,
                    "api_key": "",
                }
            },
        }

    class FakeUAVControlAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setenv("UAV_API_URL", "http://env-uav.test")
    monkeypatch.setenv("UAV_API_KEY", "env-uav-key")
    monkeypatch.setattr("agent_api_service.load_llm_settings", fake_load_llm_settings)
    monkeypatch.setattr("agent_api_service.UAVControlAgent", FakeUAVControlAgent)

    initialize_agent_from_settings()

    assert captured["base_url"] == "http://env-uav.test"
    assert captured["uav_api_key"] == "env-uav-key"
