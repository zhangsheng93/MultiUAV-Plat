"""
UAV Control Agent using modern LangChain agents.

This module preserves the public behavior of the legacy UAV agent while
switching the internal agent runtime away from langchain_classic.
"""
import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai.chat_models import base as openai_chat_base
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from blackboard import PerceptionBlackboard
from uav_api_client import UAVAPIClient
from uav_langchain_tools import create_uav_tools
from logging_config import get_logger
from template.system_prompt import build_system_prompt


logger = get_logger(__name__)


def patch_openai_compatible_reasoning_content() -> None:
    """Preserve DeepSeek thinking-mode reasoning_content across tool calls."""
    if getattr(openai_chat_base, "_uav_reasoning_content_patched", False):
        return

    original_to_message = openai_chat_base._convert_dict_to_message
    original_to_dict = openai_chat_base._convert_message_to_dict

    def convert_dict_to_message_with_reasoning(message_dict: Any) -> Any:
        message = original_to_message(message_dict)
        if (
            isinstance(message, AIMessage)
            and isinstance(message_dict, dict)
            and "reasoning_content" in message_dict
        ):
            message.additional_kwargs["reasoning_content"] = message_dict["reasoning_content"]
        return message

    def convert_message_to_dict_with_reasoning(message: Any, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        message_dict = original_to_dict(message, *args, **kwargs)
        if isinstance(message, AIMessage):
            reasoning_content = message.additional_kwargs.get("reasoning_content")
            if reasoning_content is not None:
                message_dict["reasoning_content"] = reasoning_content
        return message_dict

    openai_chat_base._convert_dict_to_message = convert_dict_to_message_with_reasoning
    openai_chat_base._convert_message_to_dict = convert_message_to_dict_with_reasoning
    openai_chat_base._uav_reasoning_content_patched = True


patch_openai_compatible_reasoning_content()


def sanitize_for_log(value: Any, max_length: int = 1000) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = " ".join(text.split())
    if len(text) > max_length:
        return f"{text[:max_length]}..."
    return text


def empty_token_usage() -> Dict[str, int]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
    }


def int_token(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def token_usage_from_dict(usage: Dict[str, Any]) -> Dict[str, int]:
    prompt_tokens = int_token(usage.get("input_tokens", usage.get("prompt_tokens")))
    completion_tokens = int_token(usage.get("output_tokens", usage.get("completion_tokens")))
    total_tokens = int_token(usage.get("total_tokens"))
    if not total_tokens:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "llm_calls": 1,
    }


def token_usage_from_message(message: Any) -> Optional[Dict[str, int]]:
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        return token_usage_from_dict(usage)

    response_metadata = getattr(message, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            return token_usage_from_dict(token_usage)

    return None


def merge_token_usage(totals: Dict[str, int], usage: Dict[str, int]) -> None:
    totals["prompt_tokens"] += usage["prompt_tokens"]
    totals["completion_tokens"] += usage["completion_tokens"]
    totals["total_tokens"] += usage["total_tokens"]
    totals["llm_calls"] += usage["llm_calls"]


def format_token_usage_for_log(token_usage: Dict[str, Any]) -> str:
    return (
        f"prompt_tokens={int_token(token_usage.get('prompt_tokens'))} "
        f"completion_tokens={int_token(token_usage.get('completion_tokens'))} "
        f"total_tokens={int_token(token_usage.get('total_tokens'))} "
        f"llm_calls={int_token(token_usage.get('llm_calls'))}"
    )


def token_usage_from_llm_result(response: Any) -> Dict[str, int]:
    totals = empty_token_usage()

    llm_output = getattr(response, "llm_output", None)
    if isinstance(llm_output, dict):
        for key in ("token_usage", "usage"):
            usage = llm_output.get(key)
            if isinstance(usage, dict):
                merge_token_usage(totals, token_usage_from_dict(usage))
        if totals["llm_calls"]:
            return totals

    for generation_group in getattr(response, "generations", []) or []:
        for generation in generation_group or []:
            message = getattr(generation, "message", None)
            if message is None:
                continue
            usage = token_usage_from_message(message)
            if usage:
                merge_token_usage(totals, usage)

    return totals


class ProviderTokenLoggingCallback(BaseCallbackHandler):
    def __init__(self, command_id: str, provider: str, model: str):
        self.command_id = command_id
        self.provider = provider
        self.model = model

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        token_usage = token_usage_from_llm_result(response)
        logger.info(
            "Provider LLM call completed command_id=%s provider=%s model=%s %s",
            self.command_id,
            self.provider,
            self.model,
            format_token_usage_for_log(token_usage),
        )


def load_llm_settings(settings_path: str = "llm_settings.json") -> Optional[Dict[str, Any]]:
    """Load LLM settings from JSON file."""
    try:
        path = Path(settings_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load LLM settings from {settings_path}: {e}")
    return None


def bool_setting(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def prompt_user_for_llm_config() -> Dict[str, Any]:
    """Prompt user to select LLM provider and model."""
    settings = load_llm_settings()

    if not settings or "provider_configs" not in settings:
        print("⚠️  No llm_settings.json found or invalid format. Using command line arguments.")
        return {}

    provider_configs = settings["provider_configs"]
    selected_provider = settings.get("selected_provider", "")

    print("\n" + "=" * 60)
    print("🤖 LLM Provider Configuration")
    print("=" * 60)

    providers = list(provider_configs.keys())
    print("\nAvailable providers:")
    for i, provider in enumerate(providers, 1):
        config = provider_configs[provider]
        default_marker = " (selected in settings)" if provider == selected_provider else ""
        print(f"  {i}. {provider}{default_marker}")
        print(f"     Type: {config.get('type', 'unknown')}")
        print(f"     Base URL: {config.get('base_url', 'N/A')}")
        print(f"     Requires API Key: {config.get('requires_api_key', False)}")

    print(f"\nSelect a provider (1-{len(providers)}) [default: {selected_provider or providers[0]}]: ", end="")
    provider_choice = input().strip()

    if not provider_choice:
        chosen_provider = selected_provider if selected_provider in providers else providers[0]
    else:
        try:
            idx = int(provider_choice) - 1
            chosen_provider = providers[idx] if 0 <= idx < len(providers) else (selected_provider or providers[0])
        except ValueError:
            chosen_provider = selected_provider or providers[0]

    config = provider_configs[chosen_provider]
    print(f"\n✅ Selected provider: {chosen_provider}")

    default_models = config.get("default_models", [])
    default_model = config.get("default_model", "")

    if default_models:
        print("\nAvailable models:")
        for i, model in enumerate(default_models, 1):
            default_marker = " (default)" if model == default_model else ""
            print(f"  {i}. {model}{default_marker}")
        print(f"  {len(default_models) + 1}. Custom model (enter manually)")

        print(f"\nSelect a model (1-{len(default_models) + 1}) [default: {default_model}]: ", end="")
        model_choice = input().strip()

        if not model_choice:
            chosen_model = default_model
        else:
            try:
                idx = int(model_choice) - 1
                if 0 <= idx < len(default_models):
                    chosen_model = default_models[idx]
                elif idx == len(default_models):
                    print("Enter custom model name: ", end="")
                    chosen_model = input().strip() or default_model
                else:
                    chosen_model = default_model
            except ValueError:
                chosen_model = default_model
    else:
        print(f"\nEnter model name [default: {default_model}]: ", end="")
        chosen_model = input().strip() or default_model

    print(f"✅ Selected model: {chosen_model}")

    provider_type = config.get("type", "ollama")
    if provider_type == "openai-compatible":
        if "api.openai.com" in config.get("base_url", ""):
            llm_provider = "openai"
        else:
            llm_provider = "openai-compatible"
    else:
        llm_provider = provider_type

    api_key = str(config.get("api_key", "") or "").strip()
    if config.get("requires_api_key", False) and not api_key:
        print("\n⚠️  This provider requires an API key.")
        print("Enter API key (or press Enter to use environment variable): ", end="")
        api_key = input().strip()

    result = {
        "llm_provider": llm_provider,
        "llm_model": chosen_model,
        "llm_base_url": config.get("base_url"),
        "llm_api_key": api_key if api_key else None,
        "provider_name": chosen_provider,
    }

    print("\n" + "=" * 60)
    print("✅ Configuration complete!")
    print("=" * 60)
    print(f"Provider: {chosen_provider}")
    print(f"Type: {llm_provider}")
    print(f"Model: {chosen_model}")
    print(f"Base URL: {config.get('base_url')}")
    if api_key:
        masked = "*" * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else "****"
        print(f"API Key: {masked}")
    print("=" * 60 + "\n")

    return result


class UAVControlAgent:
    """Intelligent agent for controlling UAVs using natural language."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        uav_api_key: Optional[str] = None,
        llm_provider: str = "ollama",
        llm_model: str = "llama2",
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
        temperature: float = 0.1,
        verbose: bool = True,
        debug: bool = False,
        share_blackboard_by_session: bool = False,
        toolchain_json_recording: bool = False,
    ):
        self.client = UAVAPIClient(base_url, api_key=uav_api_key)
        self.verbose = verbose
        self.debug = debug
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.max_iterations = 150
        self.max_empty_response_retries = 2
        self.share_blackboard_by_session = share_blackboard_by_session
        self.toolchain_json_recording = toolchain_json_recording
        self._session_blackboards: Dict[str, PerceptionBlackboard] = {}
        logger.info(
            "Initializing UAVControlAgent provider=%s model=%s base_url=%s",
            llm_provider,
            llm_model,
            base_url,
        )

        if self.debug:
            print("\n" + "=" * 60)
            print("🔧 UAV Agent Initialization - Debug Mode")
            print("=" * 60)
            print(f"UAV API Server: {base_url}")
            print(f"LLM Provider: {llm_provider}")
            print(f"LLM Model: {llm_model}")
            print(f"Temperature: {temperature}")
            print(f"Verbose: {verbose}")
            print()

        if self.debug:
            print("🔌 Testing UAV API connection...")
        session = None
        try:
            session = self.client.get_current_session()
            logger.info(
                "Connected to UAV API session_id=%s task=%s",
                session.get("id"),
                session.get("task"),
            )
            if self.debug:
                print("✅ Connected to UAV API")
                print(f"   Session: {session.get('name', 'Unknown')}")
                print(f"   Task: {session.get('task', 'Unknown')}")
                print()
        except Exception as e:
            logger.warning("Could not connect to UAV API at %s: %s", base_url, e)
            if self.debug:
                print(f"⚠️  Warning: Could not connect to UAV API: {e}")
                print(f"   Make sure the UAV server is running at {base_url}")
                print()

        self.llm = self._create_llm(
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            temperature=temperature,
        )

        if self.debug:
            print("🔧 Creating UAV control tools...")
        initial_session_id = session.get("id") if isinstance(session, dict) else None
        self.blackboard = PerceptionBlackboard(session_id=initial_session_id)
        self.tools = self._create_tools(self.blackboard)
        logger.info("Created %d UAV control tools", len(self.tools))
        if self.debug:
            print(f"✅ Created {len(self.tools)} tools")
            print(f"   Tools: {', '.join([tool.name for tool in self.tools[:5]])}...")
            print()

        if self.debug:
            print("🤖 Creating modern agent runtime...")
        self.agent = self._create_agent_runtime()
        logger.info("Agent runtime created")
        if self.debug:
            print("✅ Agent runtime created")
            print()

        if self.debug:
            print("🔄 Refreshing session context...")
        self.session_context: Dict[str, Any] = {}
        self.refresh_session_context()

        if self.debug:
            print("=" * 60)
            print("✅ UAV Agent Initialization Complete!")
            print("=" * 60)
            print()

    def _create_llm(
        self,
        llm_provider: str,
        llm_model: str,
        llm_api_key: Optional[str],
        llm_base_url: Optional[str],
        temperature: float,
    ) -> Any:
        if self.debug:
            print(f"🤖 Initializing LLM provider: {llm_provider}")

        if llm_provider == "ollama":
            if self.debug:
                print(f"   Using Ollama with model: {llm_model}")
                print("   Ollama URL: http://localhost:11434 (default)")
            llm = ChatOllama(model=llm_model, temperature=temperature)
            if self.debug:
                print("✅ Ollama LLM initialized")
                print()
            return llm

        if llm_provider not in ["openai", "openai-compatible"]:
            raise ValueError(
                f"Unknown LLM provider: {llm_provider}. "
                "Use 'ollama', 'openai', or 'openai-compatible'"
            )

        if not llm_api_key:
            raise ValueError(
                f"API key is required for {llm_provider} provider. "
                "Use --llm-api-key or set environment variable."
            )

        if llm_provider == "openai":
            final_base_url = llm_base_url or "https://api.openai.com/v1"
            provider_name = "OpenAI"
        else:
            if not llm_base_url:
                raise ValueError("llm_base_url is required for openai-compatible provider")
            final_base_url = llm_base_url
            provider_name = "OpenAI-Compatible API"

        if self.debug:
            masked = "*" * (len(llm_api_key) - 4) + llm_api_key[-4:] if len(llm_api_key) > 4 else "****"
            print(f"   Provider: {provider_name}")
            print(f"   Base URL: {final_base_url}")
            print(f"   Model: {llm_model}")
            print(f"   API Key: {masked}")

        llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            api_key=llm_api_key,
            base_url=final_base_url,
        )
        if self.debug:
            print(f"✅ {provider_name} LLM initialized")
            print()
        return llm

    def _create_tools(self, blackboard: Optional[PerceptionBlackboard] = None) -> List[Any]:
        return create_uav_tools(self.client, blackboard=blackboard)

    def _current_session_id(self) -> Optional[str]:
        try:
            session = self.client.get_current_session()
        except Exception as e:
            logger.warning("Could not determine current session for blackboard scope: %s", e)
            return None
        if not isinstance(session, dict):
            return None
        session_id = session.get("id")
        return str(session_id) if session_id else None

    def _blackboard_for_current_command(self) -> PerceptionBlackboard:
        session_id = self._current_session_id()
        if not self.share_blackboard_by_session or not session_id:
            return PerceptionBlackboard(session_id=session_id)
        blackboard = self._session_blackboards.get(session_id)
        if blackboard is None:
            blackboard = PerceptionBlackboard(session_id=session_id)
            self._session_blackboards[session_id] = blackboard
        return blackboard

    def _build_system_prompt(self) -> str:
        return build_system_prompt(self.tools)

    def _create_agent_runtime(self) -> Any:
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self._build_system_prompt(),
        )

    def _recursion_limit_for_steps(self) -> int:
        """Allow enough graph turns to complete the configured number of tool steps."""
        return max(25, self.max_iterations * 3)

    def refresh_session_context(self) -> None:
        """Refresh session context information."""
        try:
            session = self.client.get_current_session()
            self.session_context = {
                "session_id": session.get("id"),
                "task_type": session.get("task"),
                "task_description": session.get("task_description"),
                "status": session.get("status"),
            }
        except Exception as e:
            logger.warning("Could not refresh session context: %s", e)
            if self.verbose:
                print(f"Warning: Could not refresh session context: {e}")

    def get_session_summary(self) -> str:
        """Get a summary of the current session."""
        try:
            session = self.client.get_current_session()
            progress = self.client.get_task_progress()
            drones = self.client.list_drones()

            summary = f"""
=== Current Session Summary ===
Session: {session.get('name', 'Unknown')}
Task: {session.get('task', 'Unknown')} - {session.get('task_description', '')}
Status: {session.get('status', 'Unknown')}

Progress: {progress.get('progress_percentage', 0)}% ({progress.get('status_message', 'Unknown')})
Completed: {progress.get('is_completed', False)}

Drones: {len(drones)} available
"""
            for drone in drones:
                summary += (
                    f"  - {drone.get('name')} ({drone.get('id')}): {drone.get('status')}, "
                    f"Battery: {drone.get('battery_level', 0):.1f}%\n"
                )
            return summary.strip()
        except Exception as e:
            return f"Error getting session summary: {e}"

    def _normalize_tool_input(self, args: Any) -> Any:
        if isinstance(args, dict) and "input_json" in args and len(args) == 1:
            raw = args.get("input_json")
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        return args

    def _message_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(str(text))
            return "\n".join(part for part in parts if part).strip()
        if content is None:
            return ""
        return str(content)

    def _extract_intermediate_steps(self, messages: List[Any]) -> List[Any]:
        steps: List[Any] = []
        pending: Dict[str, Any] = {}

        for message in messages:
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                log_text = self._message_text(getattr(message, "content", ""))
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "unknown_tool")
                    tool_input = self._normalize_tool_input(tool_call.get("args"))
                    action = SimpleNamespace(
                        tool=tool_name,
                        tool_input=tool_input,
                        log=log_text or f"Preparing to call tool '{tool_name}'",
                        message_log=None,
                    )
                    pending[tool_call.get("id", f"{tool_name}-{len(steps)}")] = action

            tool_call_id = getattr(message, "tool_call_id", None)
            if tool_call_id and tool_call_id in pending:
                action = pending.pop(tool_call_id)
                observation = self._message_text(getattr(message, "content", ""))
                steps.append((action, observation))

        for action in pending.values():
            steps.append((action, ""))

        return steps

    @staticmethod
    def _empty_token_usage() -> Dict[str, int]:
        return empty_token_usage()

    @staticmethod
    def _int_token(value: Any) -> int:
        return int_token(value)

    def _token_usage_from_message(self, message: Any) -> Optional[Dict[str, int]]:
        return token_usage_from_message(message)

    def _extract_token_usage(self, messages: List[Any]) -> Dict[str, int]:
        totals = self._empty_token_usage()
        for message in messages:
            usage = self._token_usage_from_message(message)
            if not usage:
                continue
            merge_token_usage(totals, usage)
        return totals

    def _extract_tool_names(self, steps: List[Any]) -> List[str]:
        tool_names: List[str] = []
        for step in steps:
            action = step[0] if isinstance(step, (list, tuple)) and step else step
            tool_name = getattr(action, "tool", None)
            if tool_name:
                tool_names.append(str(tool_name))
        return tool_names

    def _ingest_stream_messages(
        self,
        messages: List[Any],
        pending: Dict[str, Any],
        steps: List[Any],
    ) -> bool:
        updated = False

        for message in messages:
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                log_text = self._message_text(getattr(message, "content", ""))
                for tool_call in tool_calls:
                    tool_call_id = tool_call.get("id", f"{tool_call.get('name', 'tool')}-{len(steps)}")
                    if tool_call_id in pending:
                        continue
                    tool_name = tool_call.get("name", "unknown_tool")
                    tool_input = self._normalize_tool_input(tool_call.get("args"))
                    pending[tool_call_id] = SimpleNamespace(
                        tool=tool_name,
                        tool_input=tool_input,
                        log=log_text or f"Preparing to call tool '{tool_name}'",
                        message_log=None,
                    )
                    steps.append((pending[tool_call_id], ""))
                    updated = True

            tool_call_id = getattr(message, "tool_call_id", None)
            if tool_call_id and tool_call_id in pending:
                observation = self._message_text(getattr(message, "content", ""))
                for idx in range(len(steps) - 1, -1, -1):
                    action, existing_observation = steps[idx]
                    if action is pending[tool_call_id]:
                        if existing_observation != observation:
                            steps[idx] = (action, observation)
                            updated = True
                        break

        return updated

    def _stream_updates_to_steps(
        self,
        command: str,
        config: Dict[str, Any],
        step_callback: Optional[Any],
    ) -> Dict[str, Any]:
        pending: Dict[str, Any] = {}
        steps: List[Any] = []
        collected_messages: List[Any] = []
        seen_message_keys: set[str] = set()
        limit_reached = False

        def message_key(message: Any) -> str:
            message_id = getattr(message, "id", None)
            if message_id:
                return str(message_id)
            tool_call_id = getattr(message, "tool_call_id", None)
            content = self._message_text(getattr(message, "content", ""))
            tool_calls = getattr(message, "tool_calls", None) or []
            return f"{message.__class__.__name__}:{tool_call_id}:{content}:{tool_calls}"

        try:
            for chunk in self.agent.stream(
                {"messages": [{"role": "user", "content": command}]},
                config=config,
                stream_mode="updates",
            ):
                for data in chunk.values():
                    messages = data.get("messages", [])
                    for message in messages:
                        key = message_key(message)
                        if key not in seen_message_keys:
                            seen_message_keys.add(key)
                            collected_messages.append(message)
                    if self._ingest_stream_messages(messages, pending, steps) and step_callback:
                        step_callback(list(steps))
                    if len(steps) >= self.max_iterations:
                        limit_reached = True
                        break
                if limit_reached:
                    break
        except Exception as e:
            return {
                "messages": collected_messages,
                "intermediate_steps": list(steps),
                "error": e,
            }

        return {
            "messages": collected_messages,
            "intermediate_steps": list(steps),
            "stopped_due_to_step_limit": limit_reached,
        }

    def _extract_final_output(self, messages: List[Any]) -> str:
        for message in reversed(messages):
            if getattr(message, "tool_call_id", None):
                continue
            if getattr(message, "tool_calls", None):
                continue
            content = self._message_text(getattr(message, "content", ""))
            if content:
                return content
        return ""

    def _last_observation_preview(self, steps: List[Any], max_length: int = 500) -> str:
        if not steps:
            return ""
        last_step = steps[-1]
        observation = ""
        if isinstance(last_step, (list, tuple)) and len(last_step) >= 2:
            observation = self._message_text(last_step[1])
        else:
            observation = self._message_text(last_step)
        return sanitize_for_log(observation, max_length=max_length)

    def _last_response_message(self, messages: List[Any]) -> Optional[Any]:
        for message in reversed(messages):
            if getattr(message, "tool_call_id", None):
                continue
            return message
        return None

    def _message_finish_reason(self, message: Any) -> Optional[str]:
        response_metadata = getattr(message, "response_metadata", None)
        if isinstance(response_metadata, dict):
            for key in ("finish_reason", "stop_reason"):
                if response_metadata.get(key):
                    return str(response_metadata[key])
            message_info = response_metadata.get("message")
            if isinstance(message_info, dict) and message_info.get("finish_reason"):
                return str(message_info["finish_reason"])
        additional_kwargs = getattr(message, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            for key in ("finish_reason", "stop_reason"):
                if additional_kwargs.get(key):
                    return str(additional_kwargs[key])
        return None

    def _log_empty_terminal_response(
        self,
        command_id: str,
        messages: List[Any],
        steps: List[Any],
        token_usage: Dict[str, Any],
        retry_index: int,
    ) -> None:
        message = self._last_response_message(messages)
        response_metadata = getattr(message, "response_metadata", None) if message is not None else None
        logger.warning(
            "Agent returned empty terminal response command_id=%s retry=%d message_class=%s "
            "content=\"%s\" tool_call_count=%d finish_reason=%s response_metadata=\"%s\" "
            "steps=%d %s last_observation=\"%s\"",
            command_id,
            retry_index,
            message.__class__.__name__ if message is not None else None,
            sanitize_for_log(self._message_text(getattr(message, "content", ""))) if message is not None else "",
            len(getattr(message, "tool_calls", None) or []) if message is not None else 0,
            self._message_finish_reason(message) if message is not None else None,
            sanitize_for_log(response_metadata, max_length=500) if response_metadata is not None else "",
            len(steps),
            format_token_usage_for_log(token_usage),
            self._last_observation_preview(steps),
        )

    def _empty_response_recovery_command(
        self,
        original_command: str,
        steps: List[Any],
        retry_index: int,
    ) -> str:
        tool_names = self._extract_tool_names(steps)
        recent_tools = ", ".join(tool_names[-10:]) if tool_names else "none"
        last_observation = self._last_observation_preview(steps, max_length=1200) or "none"
        return (
            "Continue the UAV mission after an empty assistant response.\n"
            "Do not restart or repeat completed actions unless current state verification proves it is required.\n"
            "Check the current drone/session state, continue from the last completed observation, and finish only "
            "when the mission is complete.\n"
            "The final answer must end with [TASK DONE].\n\n"
            f"Original command:\n{original_command}\n\n"
            f"Recovery attempt: {retry_index}\n"
            f"Completed tool step count: {len(steps)}\n"
            f"Recent tools: {recent_tools}\n"
            f"Last completed observation: {last_observation}"
        )

    def _incomplete_output_reason(self, output: str) -> Optional[str]:
        if not output.strip():
            return "Agent stopped without a final response; task completion was not verified."
        if "[TASK DONE]" not in output:
            return "Agent final response did not include [TASK DONE]; task completion was not verified."
        return None

    def _runtime_metadata_for_toolchain(self, empty_response_retries: int) -> Dict[str, Any]:
        session_context = getattr(self, "session_context", {}) or {}
        blackboard = getattr(self, "blackboard", None)
        session_id = session_context.get("session_id")
        if not session_id and blackboard is not None:
            session_id = getattr(blackboard, "session_id", None)
        return {
            "provider": getattr(self, "llm_provider", None),
            "model": getattr(self, "llm_model", None),
            "uav_base_url": getattr(getattr(self, "client", None), "base_url", None),
            "session_id": session_id,
            "task_type": session_context.get("task_type"),
            "task_description": session_context.get("task_description"),
            "max_iterations": getattr(self, "max_iterations", None),
            "empty_response_retries": empty_response_retries,
            "share_blackboard_by_session": getattr(self, "share_blackboard_by_session", None),
        }

    def _record_toolchain_if_enabled(
        self,
        result: Dict[str, Any],
        *,
        command_id: str,
        command: str,
        started_at: str,
        completed_at: str,
        status: str,
        empty_response_retries: int,
        tool_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not getattr(self, "toolchain_json_recording", False):
            stop_recording = getattr(getattr(self, "client", None), "stop_api_call_recording", None)
            if callable(stop_recording):
                stop_recording()
            return result

        try:
            from toolchain_recorder import (
                request_history_jsonl_path,
                tool_chain_from_steps,
                write_request_history_jsonl,
                write_toolchain_json,
            )

            steps = result.get("intermediate_steps", [])
            ordered_tool_names = tool_names if tool_names is not None else self._extract_tool_names(steps)
            get_api_calls = getattr(getattr(self, "client", None), "get_api_call_records", None)
            api_calls = get_api_calls() if callable(get_api_calls) else []
            record = {
                "schema_version": 1,
                "command_id": command_id,
                "started_at": started_at,
                "completed_at": completed_at,
                "status": status,
                "success": bool(result.get("success", False)),
                "command": command,
                "output": str(result.get("output", "")),
                "token_usage": result.get("token_usage") or self._empty_token_usage(),
                "runtime": self._runtime_metadata_for_toolchain(empty_response_retries),
                "tool_names": ordered_tool_names,
                "tool_chain": tool_chain_from_steps(steps),
                "api_calls": api_calls,
            }
            request_history_file = None
            try:
                request_history_path = request_history_jsonl_path(record)
                write_request_history_jsonl(record, api_calls)
                request_history_file = str(request_history_path)
                record["request_history_file"] = request_history_file
            except Exception as e:
                logger.warning("Could not write request-history JSONL command_id=%s error=%s", command_id, e)
            path = write_toolchain_json(record)
            recorded_result = {**result, "tool_chain_file": str(path)}
            if request_history_file is not None:
                recorded_result["request_history_file"] = request_history_file
            return recorded_result
        except Exception as e:
            logger.warning("Could not write tool-chain JSON command_id=%s error=%s", command_id, e)
            return result
        finally:
            stop_recording = getattr(getattr(self, "client", None), "stop_api_call_recording", None)
            if callable(stop_recording):
                stop_recording()

    def _run_agent_once(
        self,
        command: str,
        config: Dict[str, Any],
        step_callback: Optional[Any],
    ) -> Dict[str, Any]:
        if step_callback:
            return self._stream_updates_to_steps(command, config, step_callback)
        return self.agent.invoke(
            {"messages": [{"role": "user", "content": command}]},
            config=config,
        )

    def execute(
        self,
        command: str,
        callbacks: Optional[List[Any]] = None,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute a natural language command.

        Returns:
            Dictionary with 'output', 'intermediate_steps', and 'success' keys.
        """
        command_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        start_api_recording = getattr(getattr(self, "client", None), "start_api_call_recording", None)
        stop_api_recording = getattr(getattr(self, "client", None), "stop_api_call_recording", None)
        if getattr(self, "toolchain_json_recording", False):
            if callable(start_api_recording):
                start_api_recording()
        elif callable(stop_api_recording):
            stop_api_recording()
        sanitized_command = sanitize_for_log(command)
        logger.info(
            "Command started command_id=%s provider=%s model=%s command_length=%d command=\"%s\"",
            command_id,
            self.llm_provider,
            self.llm_model,
            len(command),
            sanitized_command,
        )
        if self.debug:
            print(f"\n{'=' * 60}")
            print("🎯 Executing Command")
            print(f"{'=' * 60}")
            print(f"Command: {command}")
            print(f"{'=' * 60}\n")

        try:
            self.blackboard = self._blackboard_for_current_command()
            self.tools = self._create_tools(self.blackboard)
            self.agent = self._create_agent_runtime()

            if self.debug:
                print("🔄 Invoking modern agent runtime...")

            config: Dict[str, Any] = {"recursion_limit": self._recursion_limit_for_steps()}
            provider_token_callback = ProviderTokenLoggingCallback(
                command_id=command_id,
                provider=self.llm_provider,
                model=self.llm_model,
            )
            config["callbacks"] = [provider_token_callback]
            if callbacks:
                config["callbacks"].extend(callbacks)

            all_intermediate_steps: List[Any] = []
            total_token_usage = self._empty_token_usage()
            empty_response_retries = 0
            current_command = command
            max_attempts = self.max_empty_response_retries + 1

            for attempt_index in range(max_attempts):
                if attempt_index > 0:
                    self.agent = self._create_agent_runtime()
                    empty_response_retries += 1

                def attempt_step_callback(attempt_steps: List[Any]) -> None:
                    if step_callback:
                        step_callback(all_intermediate_steps + list(attempt_steps))

                result = self._run_agent_once(
                    current_command,
                    config,
                    attempt_step_callback if step_callback else None,
                )

                messages = result.get("messages", [])
                output = self._extract_final_output(messages)
                attempt_steps = self._extract_intermediate_steps(messages)
                if step_callback and not attempt_steps:
                    attempt_steps = result.get("intermediate_steps", [])
                all_intermediate_steps.extend(attempt_steps)
                token_usage = self._extract_token_usage(messages)
                merge_token_usage(total_token_usage, token_usage)
                tool_names = self._extract_tool_names(all_intermediate_steps)

                stream_error = result.get("error")
                if stream_error is not None:
                    logger.error(
                        "Command failed command_id=%s error=%s %s tools=%s",
                        command_id,
                        stream_error,
                        format_token_usage_for_log(total_token_usage),
                        tool_names,
                    )
                    result_payload = {
                        "success": False,
                        "output": f"Error executing command: {str(stream_error)}",
                        "intermediate_steps": all_intermediate_steps,
                        "token_usage": total_token_usage,
                        "empty_response_retries": empty_response_retries,
                    }
                    return self._record_toolchain_if_enabled(
                        result_payload,
                        command_id=command_id,
                        command=command,
                        started_at=started_at,
                        completed_at=datetime.now().isoformat(),
                        status="stream_error",
                        empty_response_retries=empty_response_retries,
                        tool_names=tool_names,
                    )

                if result.get("stopped_due_to_step_limit") or len(all_intermediate_steps) >= self.max_iterations:
                    logger.warning(
                        "Command stopped at step limit command_id=%s steps=%d %s tools=%s",
                        command_id,
                        len(all_intermediate_steps),
                        format_token_usage_for_log(total_token_usage),
                        tool_names,
                    )
                    result_payload = {
                        "success": False,
                        "output": (
                            output
                            or f"Stopped after reaching the maximum of {self.max_iterations} ReAct tool step(s)."
                        ),
                        "intermediate_steps": all_intermediate_steps,
                        "token_usage": total_token_usage,
                        "empty_response_retries": empty_response_retries,
                    }
                    return self._record_toolchain_if_enabled(
                        result_payload,
                        command_id=command_id,
                        command=command,
                        started_at=started_at,
                        completed_at=datetime.now().isoformat(),
                        status="step_limit",
                        empty_response_retries=empty_response_retries,
                        tool_names=tool_names,
                    )

                incomplete_reason = self._incomplete_output_reason(output)
                if incomplete_reason:
                    if not output.strip() and attempt_index < max_attempts - 1:
                        self._log_empty_terminal_response(
                            command_id,
                            messages,
                            all_intermediate_steps,
                            total_token_usage,
                            empty_response_retries,
                        )
                        current_command = self._empty_response_recovery_command(
                            command,
                            all_intermediate_steps,
                            empty_response_retries + 1,
                        )
                        continue

                    logger.warning(
                        "Command stopped without verified completion command_id=%s steps=%d reason=%s retries=%d %s tools=%s last_observation=\"%s\"",
                        command_id,
                        len(all_intermediate_steps),
                        incomplete_reason,
                        empty_response_retries,
                        format_token_usage_for_log(total_token_usage),
                        tool_names,
                        self._last_observation_preview(all_intermediate_steps),
                    )
                    result_payload = {
                        "success": False,
                        "output": incomplete_reason,
                        "intermediate_steps": all_intermediate_steps,
                        "token_usage": total_token_usage,
                        "empty_response_retries": empty_response_retries,
                    }
                    return self._record_toolchain_if_enabled(
                        result_payload,
                        command_id=command_id,
                        command=command,
                        started_at=started_at,
                        completed_at=datetime.now().isoformat(),
                        status="failed",
                        empty_response_retries=empty_response_retries,
                        tool_names=tool_names,
                    )

                intermediate_steps = all_intermediate_steps
                token_usage = total_token_usage
                break
            else:
                intermediate_steps = all_intermediate_steps
                token_usage = total_token_usage
                output = ""

            if step_callback:
                step_callback(intermediate_steps)

            if self.debug:
                print(f"\n{'=' * 60}")
                print("✅ Command Execution Complete")
                print(f"{'=' * 60}")
                print("Success: True")
                print(f"Intermediate steps: {len(intermediate_steps)}")
                print(f"{'=' * 60}\n")

            logger.info(
                "Command completed command_id=%s success=True steps=%d retries=%d %s tools=%s",
                command_id,
                len(intermediate_steps),
                empty_response_retries,
                format_token_usage_for_log(token_usage),
                tool_names,
            )
            result_payload = {
                "success": True,
                "output": output,
                "intermediate_steps": intermediate_steps,
                "token_usage": token_usage,
                "empty_response_retries": empty_response_retries,
            }
            return self._record_toolchain_if_enabled(
                result_payload,
                command_id=command_id,
                command=command,
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                status="completed",
                empty_response_retries=empty_response_retries,
                tool_names=tool_names,
            )
        except Exception as e:
            logger.exception("Command failed command_id=%s error=%s", command_id, e)
            if self.debug:
                print(f"\n{'=' * 60}")
                print("❌ Command Execution Failed")
                print(f"{'=' * 60}")
                print(f"Error: {str(e)}")
                print(f"{'=' * 60}\n")

            result_payload = {
                "success": False,
                "output": f"Error executing command: {str(e)}",
                "intermediate_steps": [],
                "token_usage": self._empty_token_usage(),
            }
            return self._record_toolchain_if_enabled(
                result_payload,
                command_id=command_id,
                command=command,
                started_at=started_at,
                completed_at=datetime.now().isoformat(),
                status="exception",
                empty_response_retries=0,
                tool_names=[],
            )

    def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        print("\n" + "=" * 60)
        print("🚁 UAV Control Agent - Interactive Mode")
        print("=" * 60)
        print("\nType 'quit', 'exit', or 'q' to stop")
        print("Type 'status' to see session summary")
        print("Type 'help' for example commands\n")

        print(self.get_session_summary())
        print("\n" + "-" * 60 + "\n")

        while True:
            try:
                user_input = input("\n🎮 Command: ").strip()

                if not user_input:
                    continue
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                if user_input.lower() == "status":
                    print(self.get_session_summary())
                    continue
                if user_input.lower() == "help":
                    self._print_help()
                    continue

                print("\n🤖 Processing...\n")
                result = self.execute(user_input)
                if result["success"]:
                    print(f"\n✅ {result['output']}\n")
                else:
                    print(f"\n❌ {result['output']}\n")
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    def _print_help(self) -> None:
        help_text = """
Example Commands:
==================

Information:
- "What drones are available?"
- "Show me the current mission status"
- "What targets do I need to visit?"
- "Check the weather conditions"
- "What's the task progress?"

Basic Control:
- "Take off drone-abc123 to 15 meters"
- "Move drone-abc123 to coordinates x=100, y=50, z=20"
- "Land drone-abc123"
- "Return all drones home"

Mission Execution:
- "Visit all targets with the first drone"
- "Search the area with available drones"
- "Complete the mission task"
- "Patrol the assigned areas"

Safety:
- "Check if there are obstacles between (0,0,10) and (100,100,10)"
- "What's nearby drone-abc123?"
- "Check battery levels"

Smart Commands:
- "Take photos at all target locations"
- "Charge any drones with low battery"
- "Survey all targets and return home"
"""
        print(help_text)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="UAV Control Agent - Natural Language Drone Control"
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="UAV API base URL")
    parser.add_argument(
        "--uav-api-key",
        default=None,
        help="API key for UAV server (defaults to USER role if not provided, or set UAV_API_KEY env var)",
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        choices=["ollama", "openai", "openai-compatible"],
        help="LLM provider (ollama, openai, or openai-compatible for DeepSeek, etc.)",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model name (e.g., llama2, gpt-4o-mini, deepseek-chat)",
    )
    parser.add_argument(
        "--llm-api-key",
        default=None,
        help="API key for LLM provider (or set via environment variable)",
    )
    parser.add_argument(
        "--llm-base-url",
        default=None,
        help="Custom base URL for LLM API (required for openai-compatible providers)",
    )
    parser.add_argument("--temperature", type=float, default=0.1, help="LLM temperature (0.0-1.0)")
    parser.add_argument("--command", "-c", default=None, help="Single command to execute (non-interactive)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce verbosity")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output for connection and setup info")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Skip interactive provider/model selection (use command line args or defaults)",
    )

    args = parser.parse_args()

    should_prompt = (
        not args.no_prompt
        and not args.command
        and args.llm_provider is None
        and args.llm_model is None
    )

    if should_prompt:
        config = prompt_user_for_llm_config()
        if config:
            llm_provider = config.get("llm_provider", "ollama")
            llm_model = config.get("llm_model", "llama2")
            llm_base_url = config.get("llm_base_url")
            llm_api_key = config.get("llm_api_key")
        else:
            llm_provider = "ollama"
            llm_model = "llama2"
            llm_base_url = None
            llm_api_key = None
    else:
        llm_provider = args.llm_provider or "ollama"
        llm_model = args.llm_model or "llama2"
        llm_base_url = args.llm_base_url
        llm_api_key = args.llm_api_key

    if not llm_api_key:
        llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

    uav_api_key = args.uav_api_key or os.getenv("UAV_API_KEY")
    settings_for_agent = load_llm_settings() or {}
    share_blackboard_by_session = bool_setting(
        settings_for_agent.get("share_blackboard_by_session"),
        default=False,
    )
    toolchain_json_recording = bool_setting(
        settings_for_agent.get("toolchain_json_recording"),
        default=False,
    )

    try:
        agent = UAVControlAgent(
            base_url=args.base_url,
            uav_api_key=uav_api_key,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            temperature=args.temperature,
            verbose=not args.quiet,
            debug=args.debug,
            share_blackboard_by_session=share_blackboard_by_session,
            toolchain_json_recording=toolchain_json_recording,
        )
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        print("\nMake sure:")
        print("  - The required LangChain packages are installed")
        print("  - Ollama is running (if using --llm-provider ollama)")
        print("  - OPENAI_API_KEY is set (if using --llm-provider openai)")
        print("  - UAV API server is accessible")
        return 1

    if args.command:
        result = agent.execute(args.command)
        print(result["output"])
        return 0 if result["success"] else 1

    agent.run_interactive()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
