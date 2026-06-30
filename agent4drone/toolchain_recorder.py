"""Structured JSON export for completed UAV agent tool chains."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from logging_config import LOG_DIR


TOOLCHAIN_LOG_DIR = LOG_DIR / "toolchains"
REQUEST_HISTORY_FIELDS = [
    "index",
    "method",
    "path",
    "endpoint",
    "query_params",
    "params",
    "request_body",
    "json",
    "data",
    "status_code",
    "success",
    "response_body",
    "response",
    "error",
    "started_at",
    "completed_at",
]


def make_json_safe(value: Any) -> Any:
    """Convert runtime objects into stable JSON-compatible values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, SimpleNamespace):
        return make_json_safe(vars(value))
    if is_dataclass(value) and not isinstance(value, type):
        return make_json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, Exception):
        return str(value)
    if hasattr(value, "__dict__"):
        return make_json_safe(vars(value))
    return str(value)


def message_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
        return "\n".join(part for part in parts if part).strip()
    if value is None:
        return ""
    return str(value)


def tool_chain_from_steps(steps: List[Any]) -> List[Dict[str, Any]]:
    tool_chain: List[Dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if isinstance(step, (list, tuple)) and len(step) >= 2:
            action, observation = step[0], step[1]
        else:
            action, observation = step, ""

        if isinstance(action, dict):
            tool = action.get("tool")
            tool_input = action.get("tool_input")
            log = action.get("log")
        else:
            tool = getattr(action, "tool", None)
            tool_input = getattr(action, "tool_input", None)
            log = getattr(action, "log", None)

        tool_chain.append(
            {
                "index": index,
                "tool": str(tool) if tool is not None else "",
                "tool_input": make_json_safe(tool_input),
                "observation": make_json_safe(message_text(observation)),
                "log": message_text(log),
            }
        )
    return tool_chain


def safe_filename_part(value: Any, fallback: str = "unknown") -> str:
    text = str(value or fallback)
    safe_text = "".join(char for char in text if char.isalnum() or char in {"-", "_"})
    return safe_text or fallback


def toolchain_artifact_base_path(record: Dict[str, Any], output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = TOOLCHAIN_LOG_DIR
    completed_at = str(record.get("completed_at") or datetime.now().isoformat())
    timestamp = (
        completed_at.replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+", "_")
        .replace("Z", "")
    )
    timestamp = "".join(char for char in timestamp if char.isalnum() or char == "_")[:32]
    runtime = record.get("runtime") if isinstance(record.get("runtime"), dict) else {}
    safe_session_id = safe_filename_part(runtime.get("session_id"))
    safe_command_id = safe_filename_part(record.get("command_id"))
    safe_status = safe_filename_part(record.get("status"))
    return output_dir / f"{timestamp}_{safe_session_id}_{safe_command_id}_{safe_status}"


def toolchain_json_path(record: Dict[str, Any], output_dir: Path | None = None) -> Path:
    return toolchain_artifact_base_path(record, output_dir).with_suffix(".json")


def request_history_jsonl_path(record: Dict[str, Any], output_dir: Path | None = None) -> Path:
    base_path = toolchain_artifact_base_path(record, output_dir)
    return base_path.parent / f"{base_path.name}_request_history.jsonl"


def _atomic_write_text(final_path: Path, payload: str) -> Path:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.parent / f".{final_path.name}.{uuid.uuid4().hex}.tmp"
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, final_path)
    return final_path


def write_toolchain_json(record: Dict[str, Any], output_dir: Path | None = None) -> Path:
    final_path = toolchain_json_path(record, output_dir)

    payload = json.dumps(make_json_safe(record), ensure_ascii=False, indent=2, sort_keys=True)
    return _atomic_write_text(final_path, payload + "\n")


def replayable_request_record(api_call: Dict[str, Any]) -> Dict[str, Any]:
    safe_call = make_json_safe(api_call)
    if not isinstance(safe_call, dict):
        safe_call = {}
    endpoint = safe_call.get("endpoint")
    params = safe_call.get("params")
    request_body = safe_call.get("json")
    if request_body is None:
        request_body = safe_call.get("data")
    response = safe_call.get("response")
    enriched_call = {
        **safe_call,
        "path": safe_call.get("path") or endpoint,
        "query_params": safe_call.get("query_params") or params or {},
        "request_body": safe_call.get("request_body", request_body),
        "response_body": safe_call.get("response_body", response),
    }
    return {field: enriched_call.get(field) for field in REQUEST_HISTORY_FIELDS}


def write_request_history_jsonl(
    record: Dict[str, Any],
    api_calls: List[Dict[str, Any]],
    output_dir: Path | None = None,
) -> Path:
    final_path = request_history_jsonl_path(record, output_dir)
    lines = [
        json.dumps(replayable_request_record(api_call), ensure_ascii=False, sort_keys=True)
        for api_call in api_calls
    ]
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    return _atomic_write_text(final_path, payload)
