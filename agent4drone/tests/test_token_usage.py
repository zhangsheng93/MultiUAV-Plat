import json
from pathlib import Path
import sys
from types import SimpleNamespace

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import format_token_usage_summary
import toolchain_recorder
from uav_agent import (
    ProviderTokenLoggingCallback,
    UAVControlAgent,
    format_token_usage_for_log,
    sanitize_for_log,
    token_usage_from_llm_result,
)
from langchain_openai.chat_models import base as openai_chat_base


def _agent_without_init():
    return UAVControlAgent.__new__(UAVControlAgent)


class FakeSessionClient:
    def __init__(self, session_ids=None, fail=False):
        self.session_ids = session_ids if isinstance(session_ids, list) else [session_ids or "session-1"]
        self.fail = fail
        self.calls = 0
        self._api_call_records = None

    def start_api_call_recording(self):
        self._api_call_records = []

    def get_api_call_records(self):
        return list(self._api_call_records or [])

    def stop_api_call_recording(self):
        records = self.get_api_call_records()
        self._api_call_records = None
        return records

    def get_current_session(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("session unavailable")
        session_id = self.session_ids[min(self.calls - 1, len(self.session_ids) - 1)]
        if self._api_call_records is not None:
            self._api_call_records.append(
                {
                    "index": len(self._api_call_records) + 1,
                    "started_at": "2026-01-01T00:00:00",
                    "method": "GET",
                    "endpoint": "/sessions/current",
                    "params": {"data": "false"},
                    "json": None,
                    "data": None,
                    "success": True,
                    "status_code": 200,
                    "response": {"id": session_id},
                    "error": None,
                    "completed_at": "2026-01-01T00:00:01",
                }
            )
        return {"id": session_id}


class FakeAgentRuntime:
    def __init__(self, results):
        self.results = results if isinstance(results, list) else [results]
        self.invoke_calls = []
        self.invoke_count = 0

    def invoke(self, payload, config=None):
        self.invoke_calls.append(payload)
        result = self.results[min(self.invoke_count, len(self.results) - 1)]
        self.invoke_count += 1
        return result

    def stream(self, payload, config=None, stream_mode=None):
        self.invoke_calls.append(payload)
        result = self.results[min(self.invoke_count, len(self.results) - 1)]
        self.invoke_count += 1
        yield {"agent": {"messages": result.get("messages", [])}}


def _executable_agent(result):
    agent = _agent_without_init()
    agent.client = FakeSessionClient()
    agent.llm_provider = "test-provider"
    agent.llm_model = "test-model"
    agent.max_iterations = 150
    agent.max_empty_response_retries = 2
    agent.debug = False
    agent.share_blackboard_by_session = False
    agent.toolchain_json_recording = False
    agent._session_blackboards = {}
    agent._create_tools = lambda blackboard: []
    runtime = FakeAgentRuntime(result)
    agent._create_agent_runtime = lambda: runtime
    return agent


def _tool_step_messages(final_content):
    return [
        SimpleNamespace(
            content="",
            tool_calls=[
                {
                    "id": "call-1",
                    "name": "get_drone_status",
                    "args": {"drone_id": "drone-1"},
                }
            ],
        ),
        SimpleNamespace(
            content='{"success": true}',
            tool_call_id="call-1",
            tool_calls=[],
        ),
        SimpleNamespace(content=final_content, tool_calls=[]),
    ]


def test_extracts_usage_metadata_tokens():
    agent = _agent_without_init()
    message = SimpleNamespace(
        usage_metadata={
            "input_tokens": 12,
            "output_tokens": 8,
            "total_tokens": 20,
        }
    )

    assert agent._extract_token_usage([message]) == {
        "prompt_tokens": 12,
        "completion_tokens": 8,
        "total_tokens": 20,
        "llm_calls": 1,
    }


def test_preserves_deepseek_reasoning_content_across_tool_call_messages():
    raw_message = {
        "role": "assistant",
        "content": "",
        "reasoning_content": "Need current drone and weather state.",
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "list_drones",
                    "arguments": "{}",
                },
            }
        ],
    }

    message = openai_chat_base._convert_dict_to_message(raw_message)
    payload = openai_chat_base._convert_message_to_dict(message)

    assert message.additional_kwargs["reasoning_content"] == raw_message["reasoning_content"]
    assert payload["reasoning_content"] == raw_message["reasoning_content"]
    assert payload["tool_calls"][0]["function"]["name"] == "list_drones"


def test_execute_treats_empty_final_response_as_failure():
    agent = _executable_agent({"messages": _tool_step_messages("")})

    result = agent.execute("check drone")

    assert result["success"] is False
    assert result["output"] == "Agent stopped without a final response; task completion was not verified."
    assert result["empty_response_retries"] == 2
    assert len(result["intermediate_steps"]) == 3


def test_execute_recovers_from_empty_final_response():
    agent = _executable_agent(
        [
            {"messages": _tool_step_messages("")},
            {"messages": _tool_step_messages("Done [TASK DONE]")},
        ]
    )

    result = agent.execute("check drone")

    assert result["success"] is True
    assert result["output"] == "Done [TASK DONE]"
    assert len(result["intermediate_steps"]) == 2


def test_execute_recovers_from_streamed_empty_final_response():
    agent = _executable_agent(
        [
            {"messages": _tool_step_messages("")},
            {"messages": _tool_step_messages("Done [TASK DONE]")},
        ]
    )
    step_updates = []

    result = agent.execute("check drone", step_callback=lambda steps: step_updates.append(steps))

    assert result["success"] is True
    assert result["output"] == "Done [TASK DONE]"
    assert len(result["intermediate_steps"]) == 2
    assert len(step_updates[-1]) == 2


def test_execute_requires_task_done_marker_for_success():
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})

    result = agent.execute("check drone")

    assert result["success"] is True
    assert result["output"] == "Done [TASK DONE]"


def test_toolchain_recording_disabled_keeps_result_shape(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})

    result = agent.execute("check drone")

    assert result["success"] is True
    assert "tool_chain_file" not in result
    assert list(tmp_path.iterdir()) == []


def test_toolchain_recording_writes_success_json(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    agent.toolchain_json_recording = True

    result = agent.execute("check drone")

    assert result["success"] is True
    tool_chain_file = Path(result["tool_chain_file"])
    request_history_file = Path(result["request_history_file"])
    assert tool_chain_file.parent == tmp_path
    assert request_history_file.parent == tmp_path
    assert "_session-1_" in tool_chain_file.name
    assert request_history_file.name == tool_chain_file.name.replace(".json", "_request_history.jsonl")
    assert tool_chain_file.name.endswith("_completed.json")
    payload = json.loads(tool_chain_file.read_text(encoding="utf-8"))
    assert payload["request_history_file"] == str(request_history_file)
    assert payload["schema_version"] == 1
    assert payload["status"] == "completed"
    assert payload["success"] is True
    assert payload["command"] == "check drone"
    assert payload["output"] == "Done [TASK DONE]"
    assert payload["runtime"]["provider"] == "test-provider"
    assert payload["runtime"]["model"] == "test-model"
    assert payload["runtime"]["uav_base_url"] is None
    assert payload["runtime"]["session_id"] == "session-1"
    assert payload["api_calls"] == [
        {
            "index": 1,
            "started_at": "2026-01-01T00:00:00",
            "method": "GET",
            "endpoint": "/sessions/current",
            "params": {"data": "false"},
            "json": None,
            "data": None,
            "success": True,
            "status_code": 200,
            "response": {"id": "session-1"},
            "error": None,
            "completed_at": "2026-01-01T00:00:01",
        }
    ]
    request_history_lines = request_history_file.read_text(encoding="utf-8").splitlines()
    assert len(request_history_lines) == 1
    assert json.loads(request_history_lines[0]) == {
        "index": 1,
        "started_at": "2026-01-01T00:00:00",
        "method": "GET",
        "path": "/sessions/current",
        "endpoint": "/sessions/current",
        "query_params": {"data": "false"},
        "params": {"data": "false"},
        "request_body": None,
        "json": None,
        "data": None,
        "success": True,
        "status_code": 200,
        "response_body": {"id": "session-1"},
        "response": {"id": "session-1"},
        "error": None,
        "completed_at": "2026-01-01T00:00:01",
    }
    assert payload["tool_names"] == ["get_drone_status"]
    assert payload["tool_chain"] == [
        {
            "index": 1,
            "tool": "get_drone_status",
            "tool_input": {"drone_id": "drone-1"},
            "observation": "{\"success\": true}",
            "log": "Preparing to call tool 'get_drone_status'",
        }
    ]


def test_toolchain_recording_writes_failure_json(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent({"messages": _tool_step_messages("Done without marker")})
    agent.toolchain_json_recording = True

    result = agent.execute("check drone")

    assert result["success"] is False
    payload = json.loads(Path(result["tool_chain_file"]).read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["tool_names"] == ["get_drone_status"]
    assert Path(result["request_history_file"]).exists()


def test_toolchain_recording_writes_step_limit_json(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent(
        {
            "messages": _tool_step_messages(""),
            "stopped_due_to_step_limit": True,
        }
    )
    agent.toolchain_json_recording = True

    result = agent.execute("check drone")

    assert result["success"] is False
    payload = json.loads(Path(result["tool_chain_file"]).read_text(encoding="utf-8"))
    assert payload["status"] == "step_limit"
    assert payload["tool_names"] == ["get_drone_status"]
    assert Path(result["request_history_file"]).exists()


def test_toolchain_recording_writes_stream_error_json(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent(
        {
            "messages": _tool_step_messages(""),
            "error": RuntimeError("stream failed"),
        }
    )
    agent.toolchain_json_recording = True

    result = agent.execute("check drone")

    assert result["success"] is False
    payload = json.loads(Path(result["tool_chain_file"]).read_text(encoding="utf-8"))
    assert payload["status"] == "stream_error"
    assert payload["tool_names"] == ["get_drone_status"]
    assert Path(result["request_history_file"]).exists()


def test_toolchain_recording_writes_exception_json(monkeypatch, tmp_path):
    monkeypatch.setattr(toolchain_recorder, "TOOLCHAIN_LOG_DIR", tmp_path)
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    agent.toolchain_json_recording = True

    def fail_create_tools(blackboard):
        raise RuntimeError("setup failed")

    agent._create_tools = fail_create_tools

    result = agent.execute("check drone")

    assert result["success"] is False
    payload = json.loads(Path(result["tool_chain_file"]).read_text(encoding="utf-8"))
    assert payload["status"] == "exception"
    assert payload["tool_names"] == []
    assert payload["tool_chain"] == []
    assert Path(result["request_history_file"]).exists()


def test_request_history_jsonl_writer_uses_toolchain_base_name(tmp_path):
    record = {
        "completed_at": "2026-01-02T03:04:05.123456",
        "command_id": "command/1",
        "status": "completed",
        "runtime": {"session_id": "session-1"},
    }
    api_calls = [
        {
            "index": 1,
            "method": "POST",
            "endpoint": "/drones/drone-1/command/move_to",
            "params": {"x": 1, "y": 2, "z": 3},
            "json": None,
            "data": None,
            "status_code": 200,
            "success": True,
            "response": {"success": True},
            "error": None,
            "started_at": "2026-01-02T03:04:05",
            "completed_at": "2026-01-02T03:04:06",
            "ignored": "not replayable",
        }
    ]

    toolchain_path = toolchain_recorder.write_toolchain_json(record, tmp_path)
    request_history_path = toolchain_recorder.write_request_history_jsonl(record, api_calls, tmp_path)

    assert request_history_path.name == toolchain_path.name.replace(".json", "_request_history.jsonl")
    lines = request_history_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "index": 1,
        "method": "POST",
        "path": "/drones/drone-1/command/move_to",
        "endpoint": "/drones/drone-1/command/move_to",
        "query_params": {"x": 1, "y": 2, "z": 3},
        "params": {"x": 1, "y": 2, "z": 3},
        "request_body": None,
        "json": None,
        "data": None,
        "status_code": 200,
        "success": True,
        "response_body": {"success": True},
        "response": {"success": True},
        "error": None,
        "started_at": "2026-01-02T03:04:05",
        "completed_at": "2026-01-02T03:04:06",
    }


def test_replayable_request_record_adds_ui_compatible_move_to_fields():
    replay_record = toolchain_recorder.replayable_request_record(
        {
            "index": 2,
            "method": "POST",
            "endpoint": "/drones/aac336ab/command/move_to",
            "params": {"x": 389.0, "y": 281.0, "z": 13.0},
            "json": None,
            "data": None,
            "status_code": 200,
            "success": True,
            "response": {"status": "success"},
            "error": None,
        }
    )

    assert replay_record["path"] == "/drones/aac336ab/command/move_to"
    assert replay_record["endpoint"] == "/drones/aac336ab/command/move_to"
    assert replay_record["query_params"] == {"x": 389.0, "y": 281.0, "z": 13.0}
    assert replay_record["params"] == {"x": 389.0, "y": 281.0, "z": 13.0}
    assert replay_record["request_body"] is None
    assert replay_record["response_body"] == {"status": "success"}


def test_toolchain_recorder_serializes_namespace_steps():
    steps = [
        (
            SimpleNamespace(
                tool="move_to",
                tool_input={"drone_id": "drone-1", "x": 1.5, "y": 2},
                log="Moving",
                ignored=object(),
            ),
            {"success": True},
        )
    ]

    tool_chain = toolchain_recorder.tool_chain_from_steps(steps)

    assert tool_chain == [
        {
            "index": 1,
            "tool": "move_to",
            "tool_input": {"drone_id": "drone-1", "x": 1.5, "y": 2},
            "observation": "{'success': True}",
            "log": "Moving",
        }
    ]


def test_execute_preserves_step_limit_failure():
    agent = _executable_agent(
        {
            "messages": _tool_step_messages(""),
            "stopped_due_to_step_limit": True,
        }
    )

    result = agent.execute("check drone")

    assert result["success"] is False
    assert "maximum of 150" in result["output"]
    assert result["empty_response_retries"] == 0


def test_execute_uses_new_blackboard_per_command_by_default():
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    captured_blackboards = []
    agent._create_tools = lambda blackboard: captured_blackboards.append(blackboard) or []

    first = agent.execute("first command")
    second = agent.execute("second command")

    assert first["success"] is True
    assert second["success"] is True
    assert len(captured_blackboards) == 2
    assert captured_blackboards[0] is not captured_blackboards[1]
    assert [blackboard.session_id for blackboard in captured_blackboards] == ["session-1", "session-1"]


def test_execute_reuses_blackboard_for_same_session_when_enabled():
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    agent.share_blackboard_by_session = True
    captured_blackboards = []
    agent._create_tools = lambda blackboard: captured_blackboards.append(blackboard) or []

    agent.execute("first command")
    agent.execute("second command")

    assert len(captured_blackboards) == 2
    assert captured_blackboards[0] is captured_blackboards[1]
    assert captured_blackboards[0].session_id == "session-1"
    assert agent._session_blackboards == {"session-1": captured_blackboards[0]}


def test_execute_uses_different_shared_blackboard_when_session_changes():
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    agent.client = FakeSessionClient(["session-1", "session-2"])
    agent.share_blackboard_by_session = True
    captured_blackboards = []
    agent._create_tools = lambda blackboard: captured_blackboards.append(blackboard) or []

    agent.execute("first command")
    agent.execute("second command")

    assert len(captured_blackboards) == 2
    assert captured_blackboards[0] is not captured_blackboards[1]
    assert [blackboard.session_id for blackboard in captured_blackboards] == ["session-1", "session-2"]
    assert set(agent._session_blackboards) == {"session-1", "session-2"}


def test_execute_falls_back_to_command_blackboard_without_session_id():
    agent = _executable_agent({"messages": _tool_step_messages("Done [TASK DONE]")})
    agent.client = FakeSessionClient(fail=True)
    agent.share_blackboard_by_session = True
    captured_blackboards = []
    agent._create_tools = lambda blackboard: captured_blackboards.append(blackboard) or []

    agent.execute("first command")
    agent.execute("second command")

    assert len(captured_blackboards) == 2
    assert captured_blackboards[0] is not captured_blackboards[1]
    assert [blackboard.session_id for blackboard in captured_blackboards] == [None, None]
    assert agent._session_blackboards == {}


def test_extracts_response_metadata_token_usage():
    agent = _agent_without_init()
    message = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
        }
    )

    assert agent._extract_token_usage([message]) == {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
        "llm_calls": 1,
    }


def test_missing_token_metadata_returns_zero_totals():
    agent = _agent_without_init()

    assert agent._extract_token_usage([SimpleNamespace(content="done")]) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
    }


def test_multiple_llm_messages_are_summed():
    agent = _agent_without_init()
    messages = [
        SimpleNamespace(usage_metadata={"input_tokens": 2, "output_tokens": 3}),
        SimpleNamespace(
            response_metadata={
                "token_usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 7,
                    "total_tokens": 12,
                }
            }
        ),
    ]

    assert agent._extract_token_usage(messages) == {
        "prompt_tokens": 7,
        "completion_tokens": 10,
        "total_tokens": 17,
        "llm_calls": 2,
    }


def test_format_token_usage_summary():
    assert (
        format_token_usage_summary(
            {
                "prompt_tokens": 1,
                "completion_tokens": 2,
                "total_tokens": 3,
                "llm_calls": 4,
            }
        )
        == "Token usage: prompt 1, completion 2, total 3, LLM calls 4"
    )


def test_format_token_usage_summary_unavailable():
    assert format_token_usage_summary(None) == "Token usage: unavailable"


def test_format_token_usage_for_log_uses_plain_fields():
    assert (
        format_token_usage_for_log(
            {
                "prompt_tokens": 7124,
                "completion_tokens": 118,
                "total_tokens": 7242,
                "llm_calls": 1,
            }
        )
        == "prompt_tokens=7124 completion_tokens=118 total_tokens=7242 llm_calls=1"
    )


def test_sanitize_for_log_replaces_newlines_and_tabs():
    assert sanitize_for_log("take off\nthen\tland\rnow") == "take off then land now"


def test_extracts_token_usage_from_llm_result_output():
    response = SimpleNamespace(
        llm_output={
            "token_usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4,
                "total_tokens": 7,
            }
        },
        generations=[],
    )

    assert token_usage_from_llm_result(response) == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
        "llm_calls": 1,
    }


def test_extracts_token_usage_from_llm_result_generations():
    response = SimpleNamespace(
        llm_output=None,
        generations=[
            [
                SimpleNamespace(
                    message=SimpleNamespace(
                        usage_metadata={
                            "input_tokens": 9,
                            "output_tokens": 6,
                            "total_tokens": 15,
                        }
                    )
                )
            ]
        ],
    )

    assert token_usage_from_llm_result(response) == {
        "prompt_tokens": 9,
        "completion_tokens": 6,
        "total_tokens": 15,
        "llm_calls": 1,
    }


def test_provider_token_logging_callback_logs_provider_usage(caplog):
    callback = ProviderTokenLoggingCallback(
        command_id="cmd-1",
        provider="openai-compatible",
        model="test-model",
    )
    response = SimpleNamespace(
        llm_output={
            "token_usage": {
                "prompt_tokens": 1,
                "completion_tokens": 2,
                "total_tokens": 3,
            }
        },
        generations=[],
    )

    callback.on_llm_end(response)

    assert "Provider LLM call completed command_id=cmd-1" in caplog.text
    assert "prompt_tokens=1 completion_tokens=2 total_tokens=3 llm_calls=1" in caplog.text
