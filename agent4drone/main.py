import json
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Any, Dict, List, Optional

from uav_agent import UAVControlAgent, bool_setting, load_llm_settings
from uav_agent import format_token_usage_for_log
from logging_config import get_logger
from pathlib import Path

# Try to import speech recognition with fallback
try:
    import speech_recognition as sr
    import pyaudio
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
    SPEECH_AVAILABLE = True
    AUDIO_AVAILABLE = True
    WHISPER_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    AUDIO_AVAILABLE = False
    WHISPER_AVAILABLE = False
    sr = None

CONFIG_FILE = "llm_settings.json"
CHAT_ICONS = {
    "You": "🧑‍✈️",
    "UAV Agent": "🤖",
    "System": "ℹ️",
    "Session Summary": "📋",
}
DEFAULT_CHAT_ICON = "💬"
logger = get_logger("ui_interface")


# ------------------------------------------------------------------ #
# Configuration utilities (shared between GUI and CLI)
# ------------------------------------------------------------------ #
def format_token_usage_summary(token_usage: Optional[Dict[str, Any]]) -> str:
    if token_usage is None:
        return "Token usage: unavailable"

    def token_int(key: str) -> int:
        try:
            return int(token_usage.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0

    return (
        "Token usage: "
        f"prompt {token_int('prompt_tokens')}, "
        f"completion {token_int('completion_tokens')}, "
        f"total {token_int('total_tokens')}, "
        f"LLM calls {token_int('llm_calls')}"
    )


def save_llm_settings(settings: Dict[str, Any], settings_path: str = CONFIG_FILE) -> None:
    """Save LLM settings to JSON file"""
    try:
        path = Path(settings_path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save LLM settings to {settings_path}: {e}")


class UAVAgentGUI:
    """
    Tkinter-based control panel for the UAV agent.

    This class focuses on GUI presentation and user interaction.
    Core business logic (LLM setup, agent execution, UAV API calls) is delegated
    to UAVControlAgent class from uav_agent_new.py.

    Responsibilities:
    - GUI layout and widget management
    - User input handling (commands, configuration)
    - Displaying results and status updates
    - Voice input UI (if available)
    - Threading for non-blocking operations

    NOT responsible for:
    - LLM initialization (handled by UAVControlAgent)
    - UAV API communication (handled by UAVControlAgent)
    - Command execution logic (handled by UAVControlAgent)
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("UAV Control Interface")
        self.root.geometry("700x800")
        self.root.configure(bg="#f0f0f0")

        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "img",
            "bot.png",
        )
        if os.path.exists(icon_path):
            try:
                self.root.iconphoto(False, tk.PhotoImage(file=icon_path))
            except tk.TclError:
                pass

        self.provider_var = tk.StringVar(value="Ollama")
        self.model_var = tk.StringVar()
        self.uav_base_url_var = tk.StringVar()
        self.uav_api_key_var = tk.StringVar()  # UAV API key for authentication
        self.temperature_var = tk.DoubleVar(value=0.1)
        self.verbose_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=True)
        self.share_blackboard_by_session_var = tk.BooleanVar(value=False)
        self.toolchain_json_recording_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="🛠️ Configure connection and initialize the agent.")

        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            CONFIG_FILE,
        )
        self.provider_configs: Dict[str, Dict[str, Any]] = {
            "Ollama": {
                "type": "ollama",
                "base_url": "http://localhost:11434",
                "default_model": "llama2",
                "default_models": [],
                "requires_api_key": False,
                "api_key": "",
            },
            "OpenAI": {
                "type": "openai-compatible",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4o-mini",
                "default_models": [
                    "gpt-4o-mini",
                    "gpt-4o",
                    "gpt-4.1-mini",
                    "gpt-3.5-turbo",
                ],
                "requires_api_key": True,
                "api_key": "",
            },
        }

        self.agent: Optional[UAVControlAgent] = None
        self.agent_lock = threading.Lock()

        # Speech recognition setup
        self.is_listening = False
        self.voice_dialog = None
        self.model_dtype = None
        self.whisper_model_var = tk.StringVar(value="large")
        self.recognizer = None
        self.whisper_model = None
        self.whisper_processor = None
        self.whisper_pipeline = None
        self.voice_enabled = False
        self.loading_whisper = False
        self.pending_voice_start = False
        self.current_whisper_model = None
        self.pending_model_reload = None
        self.voice_stop_event = None
        self.voice_recording_thread = None
        self.voice_transcribe_requested = False
        self.voice_cancel_btn = None
        self.voice_done_btn = None
        self.voice_status_label = None

        self.load_app_config()
        self.setup_ui()
        self.update_provider_dropdown()
        self.on_provider_change()
        self.root.after(400, lambda: self.initialize_agent(show_warnings=False))
        if SPEECH_AVAILABLE and AUDIO_AVAILABLE and WHISPER_AVAILABLE:
            self.root.after(200, self.load_whisper_pipeline)

    # ------------------------------------------------------------------ #
    # Configuration handling
    # ------------------------------------------------------------------ #
    def ensure_config_defaults(
        self,
        name: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fill in missing fields for a provider configuration."""
        merged = dict(config)
        defaults = self.provider_configs.get(name, {})
        for key, value in defaults.items():
            merged.setdefault(key, value)
        merged.setdefault("default_models", [])
        if isinstance(merged.get("default_models"), str):
            merged["default_models"] = [merged["default_models"]]
        merged["api_key"] = str(merged.get("api_key") or "")
        merged["default_model"] = merged.get("default_model") or ""
        merged["base_url"] = merged.get("base_url") or defaults.get("base_url", "")
        merged["requires_api_key"] = bool(merged.get("requires_api_key", False))
        return merged

    def load_app_config(self) -> None:
        """Load shared LLM provider settings from disk using shared function."""
        settings = load_llm_settings(self.config_path)
        if settings:
            if "provider_configs" in settings:
                for name, cfg in settings["provider_configs"].items():
                    self.provider_configs[name] = self.ensure_config_defaults(name, cfg)
                selected = settings.get("selected_provider")
                if selected and selected in self.provider_configs:
                    self.provider_var.set(selected)
            # Load UAV settings
            if "uav_base_url" in settings:
                self.uav_base_url_var.set(settings["uav_base_url"])
            if "uav_api_key" in settings:
                self.uav_api_key_var.set(settings["uav_api_key"])
            self.share_blackboard_by_session_var.set(
                bool_setting(settings.get("share_blackboard_by_session"), default=False)
            )
            self.toolchain_json_recording_var.set(
                bool_setting(settings.get("toolchain_json_recording"), default=False)
            )
        else:
            # Seed OpenAI key from environment if config missing
            env_key = os.getenv("OPENAI_API_KEY", "").strip()
            if env_key and "OpenAI" in self.provider_configs:
                self.provider_configs["OpenAI"]["api_key"] = env_key

        current_provider = self.provider_configs.get(self.provider_var.get())
        if current_provider and current_provider.get("default_model"):
            self.model_var.set(current_provider["default_model"])
        else:
            self.model_var.set("")

    def save_app_config(self) -> None:
        """Persist provider configuration back to disk using shared function."""
        data = {
            "selected_provider": self.provider_var.get(),
            "uav_base_url": self.uav_base_url_var.get(),
            "uav_api_key": self.uav_api_key_var.get(),
            "share_blackboard_by_session": bool(self.share_blackboard_by_session_var.get()),
            "toolchain_json_recording": bool(self.toolchain_json_recording_var.get()),
            "provider_configs": self.provider_configs,
        }
        save_llm_settings(data, self.config_path)

    def get_current_provider_config(self) -> Optional[Dict[str, Any]]:
        """Return the config object for the active provider."""
        return self.provider_configs.get(self.provider_var.get())

    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #
    def setup_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # title = ttk.Label(
        #     main_frame,
        #     text="UAV Control Interface",
        #     font=("Arial", 18, "bold"),
        # )
        # title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        config_frame = ttk.LabelFrame(main_frame, text="LLM Provider", padding=10)
        config_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for col_idx in range(4):
            config_frame.columnconfigure(col_idx, weight=1 if col_idx == 1 else 0)

        ttk.Label(config_frame, text="Provider:").grid(row=0, column=0, sticky="w")
        self.provider_dropdown = ttk.Combobox(
            config_frame,
            textvariable=self.provider_var,
            state="readonly",
            width=15,
        )
        self.provider_dropdown.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))
        self.provider_dropdown.bind("<<ComboboxSelected>>", lambda _: self.on_provider_change())

        ttk.Button(
            config_frame,
            text="Configure",
            command=self.open_provider_dialog,
            width=10,
        ).grid(row=0, column=2)

        ttk.Label(config_frame, text="Model:").grid(row=1, column=0, sticky="w")
        self.model_dropdown = ttk.Combobox(
            config_frame,
            textvariable=self.model_var,
            width=15,
        )
        self.model_dropdown.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        # Temperature label and spinbox combined in one frame, aligned with Configure button
        temp_frame = ttk.Frame(config_frame)
        temp_frame.grid(row=1, column=2, padx=(10, 0), sticky="e")
        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT, padx=(0, 5))
        temp_spin = ttk.Spinbox(
            temp_frame,
            textvariable=self.temperature_var,
            from_=0.0,
            to=1.0,
            increment=0.05,
            format="%.2f",
            width=6,
        )
        temp_spin.pack(side=tk.LEFT)

        check_frame = ttk.Frame(config_frame)
        check_frame.grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Checkbutton(check_frame, text="Verbose", variable=self.verbose_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(check_frame, text="Debug", variable=self.debug_var).pack(side=tk.LEFT)

        uav_frame = ttk.LabelFrame(main_frame, text="UAV Connection", padding=10)
        uav_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        uav_frame.columnconfigure(1, weight=1)

        ttk.Label(uav_frame, text="UAV API Base URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(uav_frame, textvariable=self.uav_base_url_var).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(uav_frame, text="Reload Agent", command=self.initialize_agent).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(uav_frame, text="Session Summary", command=lambda: self.refresh_session_summary()).grid(row=0, column=3, padx=(10, 0))

        ttk.Label(uav_frame, text="API Key (Optional):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        api_key_entry = ttk.Entry(uav_frame, textvariable=self.uav_api_key_var)
        api_key_entry.grid(row=1, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(6, 0))

        # Add tooltip/hint label
        hint_label = ttk.Label(uav_frame, text="Leave empty for AGENT role, or enter USER/SYSTEM/ADMIN key", font=("Arial", 9), foreground="gray")
        hint_label.grid(row=2, column=1, columnspan=3, sticky="w", padx=(6, 0), pady=(2, 0))

        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        main_frame.rowconfigure(3, weight=4)

        chat_frame = ttk.Frame(notebook)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        self.chat_output = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_output.grid(row=0, column=0, sticky="nsew")
        self.chat_output.configure(height=22, font=("Arial", 11))
        notebook.add(chat_frame, text="Conversation")

        steps_frame = ttk.Frame(notebook)
        steps_frame.columnconfigure(0, weight=1)
        steps_frame.rowconfigure(0, weight=1)
        self.steps_output = scrolledtext.ScrolledText(steps_frame, wrap=tk.WORD, state=tk.DISABLED, height=8)
        self.steps_output.configure(font=("Courier New", 10))
        self.steps_output.grid(row=0, column=0, sticky="nsew")
        notebook.add(steps_frame, text="Intermediate Steps")

        input_frame = ttk.LabelFrame(main_frame, text="Command", padding=3)
        input_frame.grid(row=4, column=0, sticky="ew")
        input_frame.columnconfigure(0, weight=1)

        self.command_input = tk.Text(input_frame, height=5, wrap=tk.WORD)
        self.command_input.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        input_frame.rowconfigure(0, weight=1)
        self.command_input.bind("<Return>", self.handle_command_return)
        self.command_input.bind("<KP_Enter>", self.handle_command_return)

        button_bar = ttk.Frame(input_frame)
        button_bar.grid(row=1, column=0, sticky="e")
        
        self.send_button = ttk.Button(button_bar, text="Send Command", command=self.send_command)
        self.send_button.pack(side=tk.RIGHT, padx=(6, 0))

        # Voice button
        if SPEECH_AVAILABLE and AUDIO_AVAILABLE and WHISPER_AVAILABLE:
            voice_text = "🎤 Loading.."
        else:
            voice_text = "🎤 Unavailable"

        self.voice_btn = ttk.Button(button_bar, text=voice_text, command=self.toggle_voice_input, state=tk.DISABLED)
        self.voice_btn.pack(side=tk.RIGHT, padx=(6, 0))

        ttk.Button(button_bar, text="Clear", command=lambda: self.command_input.delete("1.0", tk.END)).pack(side=tk.RIGHT, padx=(6, 0))

        

        status_bar = ttk.Frame(main_frame)
        status_bar.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        status_bar.columnconfigure(0, weight=1)
        ttk.Label(status_bar, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #
    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def append_chat(self, speaker: str, message: str) -> None:
        text = self.stringify(message)
        icon = CHAT_ICONS.get(speaker, DEFAULT_CHAT_ICON)
        self.chat_output.config(state=tk.NORMAL)
        self.chat_output.insert(tk.END, f"{icon} {speaker}: {text.strip()}\n\n")
        self.chat_output.see(tk.END)
        self.chat_output.config(state=tk.DISABLED)

    def append_steps(self, text: str) -> None:
        self.steps_output.config(state=tk.NORMAL)
        self.steps_output.delete("1.0", tk.END)
        self.steps_output.insert(tk.END, text.strip() + "\n")
        self.steps_output.see(tk.END)
        self.steps_output.config(state=tk.DISABLED)

    def clear_steps(self) -> None:
        self.steps_output.config(state=tk.NORMAL)
        self.steps_output.delete("1.0", tk.END)
        self.steps_output.config(state=tk.DISABLED)

    def update_provider_dropdown(self) -> None:
        provider_names = sorted(self.provider_configs.keys())
        self.provider_dropdown["values"] = provider_names
        if self.provider_var.get() not in provider_names and provider_names:
            self.provider_var.set(provider_names[0])

    def on_provider_change(self) -> None:
        config = self.get_current_provider_config()
        if not config:
            return

        models = self.collect_model_choices(config)
        self.model_dropdown["values"] = models
        if models:
            if self.model_var.get() not in models:
                self.model_var.set(models[0])
        else:
            self.model_var.set(config.get("default_model", ""))

        self.save_app_config()

    def collect_model_choices(self, config: Dict[str, Any]) -> List[str]:
        models: List[str] = []
        stored = config.get("default_models", [])
        if isinstance(stored, list):
            models.extend([str(item) for item in stored if item])
        elif isinstance(stored, str) and stored:
            models.append(stored)
        default_model = config.get("default_model")
        if default_model and default_model not in models:
            models.insert(0, default_model)
        return models

    # ------------------------------------------------------------------ #
    # Agent lifecycle
    # ------------------------------------------------------------------ #
    def initialize_agent(self, show_warnings: bool = True) -> None:
        thread = threading.Thread(
            target=self._initialize_agent_worker,
            args=(show_warnings,),
            daemon=True,
        )
        thread.start()

    def _initialize_agent_worker(self, show_warnings: bool) -> None:
        """Worker thread to initialize the agent - delegates to UAVControlAgent."""
        with self.agent_lock:
            config = self.get_current_provider_config()
            if not config:
                if show_warnings:
                    self.root.after(0, lambda: messagebox.showerror("Provider", "No provider configuration found."))
                else:
                    self.root.after(0, lambda: self.set_status("⚙️ Configure a provider to initialize the agent."))
                return

            # Extract configuration parameters
            llm_params = self._extract_llm_params(config)
            if llm_params is None:
                # Error already handled in _extract_llm_params
                return

            # Get UAV connection parameters
            uav_base_url = self.uav_base_url_var.get().strip() or "http://localhost:8000"
            uav_api_key = self.uav_api_key_var.get().strip() or None
            temperature = float(self.temperature_var.get())
            verbose = bool(self.verbose_var.get())
            debug = bool(self.debug_var.get())
            share_blackboard_by_session = bool(self.share_blackboard_by_session_var.get())
            toolchain_json_recording = bool(self.toolchain_json_recording_var.get())

            self.root.after(0, lambda: self.set_status("🛠️ Initializing UAV agent..."))

            # Delegate to UAVControlAgent - it handles all LLM initialization logic
            try:
                agent = UAVControlAgent(
                    base_url=uav_base_url,
                    uav_api_key=uav_api_key,
                    llm_provider=llm_params['llm_provider'],
                    llm_model=llm_params['llm_model'],
                    llm_api_key=llm_params['llm_api_key'],
                    llm_base_url=llm_params['llm_base_url'],
                    temperature=temperature,
                    verbose=verbose,
                    debug=debug,
                    share_blackboard_by_session=share_blackboard_by_session,
                    toolchain_json_recording=toolchain_json_recording,
                )
            except Exception as exc:
                if show_warnings:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror("Agent Initialization", f"Failed to initialize agent:\n{exc}"),
                    )
                else:
                    self.root.after(0, lambda: self.append_chat("System", f"⚠️ Agent initialization failed: {exc}"))
                self.root.after(0, lambda: self.set_status("❌ Agent initialization failed."))
                return

            self.agent = agent
            model_name = llm_params['llm_model']
            self.root.after(0, lambda: self.set_status("✅ Agent ready."))
            self.root.after(0, lambda: self.append_chat("System", f"🚀 Agent initialized with model '{model_name or 'default'}'."))
            self.root.after(0, lambda: self.refresh_session_summary(silent=True))

    def _extract_llm_params(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and validate LLM parameters from provider config."""
        provider_type = config.get("type", "ollama")
        base_url = config.get("base_url", "").strip()
        model = self.model_var.get().strip() or config.get("default_model", "")
        api_key = str(config.get("api_key", "") or "").strip()

        # Determine provider type
        if provider_type == "ollama":
            llm_provider = "ollama"
            llm_base_url = None
        else:
            if "api.openai.com" in base_url:
                llm_provider = "openai"
            else:
                llm_provider = "openai-compatible"
            llm_base_url = base_url or None

        # Check API key requirement
        if config.get("requires_api_key") and not api_key:
            self.root.after(
                0,
                lambda: messagebox.showwarning("API Key", "The selected provider requires an API key."),
            )
            self.root.after(0, lambda: self.set_status("🔑 Add an API key to initialize this provider."))
            return None

        return {
            'llm_provider': llm_provider,
            'llm_model': model,
            'llm_api_key': api_key or None,
            'llm_base_url': llm_base_url
        }

    # ------------------------------------------------------------------ #
    # Session summary
    # ------------------------------------------------------------------ #
    def refresh_session_summary(self, silent: bool = False) -> None:
        if not self.agent:
            if silent:
                self.set_status("ℹ️ Initialize the agent to view the session summary.")
            else:
                messagebox.showinfo("UAV Agent", "Initialize the agent first.")
            return
        thread = threading.Thread(
            target=self._fetch_session_summary,
            args=(silent,),
            daemon=True,
        )
        thread.start()

    def _fetch_session_summary(self, silent: bool) -> None:
        """Fetch session summary - delegates to UAVControlAgent method."""
        with self.agent_lock:
            if not self.agent:
                return
            self.root.after(0, lambda: self.set_status("📡 Fetching session summary..."))
            try:
                # Delegate to agent's get_session_summary method
                summary = self.agent.get_session_summary()
            except Exception as exc:
                if silent:
                    self.root.after(0, lambda: self.append_chat("System", f"⚠️ Failed to fetch session summary: {exc}"))
                else:
                    self.root.after(
                        0,
                        lambda: messagebox.showerror("Session Summary", f"Failed to fetch session summary:\n{exc}"),
                    )
                self.root.after(0, lambda: self.set_status("⚠️ Failed to fetch session summary."))
                return

            self.root.after(0, lambda: self.append_chat("Session Summary", summary.strip()))
            self.root.after(0, lambda: self.set_status("📋 Session summary updated."))

    # ------------------------------------------------------------------ #
    # Command execution
    # ------------------------------------------------------------------ #
    def handle_command_return(self, event: Any) -> Optional[str]:
        if event is None:
            return None
        if event.state & 0x1:  # Shift modifier adds newline
            return None
        self.send_command()
        return "break"

    def send_command(self) -> None:
        command = self.command_input.get("1.0", tk.END).strip()
        if not command:
            return
        if not self.agent:
            messagebox.showwarning("UAV Agent", "Initialize the agent before sending commands.")
            return

        self.append_chat("You", command)
        self.command_input.delete("1.0", tk.END)
        self.clear_steps()
        self.send_button.configure(state=tk.DISABLED)
        self.set_status("🧠 Executing command...")

        thread = threading.Thread(target=self._execute_command, args=(command,), daemon=True)
        thread.start()

    def _execute_command(self, command: str) -> None:
        """Execute command - delegates to UAVControlAgent.execute() method."""
        with self.agent_lock:
            if not self.agent:
                self.root.after(0, lambda: self.set_status("ℹ️ Agent not initialized."))
                return
            try:
                logger.info("GUI command started command_length=%d", len(command))
                def on_step_update(steps: List[Any]) -> None:
                    steps_text = self._format_intermediate_steps(steps)
                    self.root.after(0, lambda: self.append_steps(steps_text))
                    if steps:
                        self.root.after(0, lambda: self.set_status(f"🧠 Executing command [Step {len(steps)}]..."))
                    else:
                        self.root.after(0, lambda: self.set_status("🧠 Executing command..."))

                # Delegate to agent's execute method - it handles all LLM interaction
                result = self.agent.execute(command, step_callback=on_step_update)
            except Exception as exc:
                logger.exception("GUI command failed: %s", exc)
                self.root.after(0, lambda: self.append_chat("System", f"Error executing command: {exc}"))
                self.root.after(0, lambda: self.set_status("⚠️ Command failed."))
                self.root.after(0, lambda: self.send_button.configure(state=tk.NORMAL))
                return

        success = result.get("success", False)
        output = result.get("output", "")
        steps_text = self._format_intermediate_steps(result.get("intermediate_steps", []))
        token_text = format_token_usage_summary(result.get("token_usage"))
        steps_text = f"{steps_text}\n\n{token_text}" if steps_text else token_text
        logger.info(
            "GUI command completed success=%s %s",
            success,
            format_token_usage_for_log(result.get("token_usage") or {}),
        )

        display_output = output or "Agent stopped without a final response; task completion was not verified."
        self.root.after(0, lambda: self.append_chat("UAV Agent", display_output if display_output else "(no response)"))
        self.root.after(0, lambda: self.append_steps(steps_text))
        self.root.after(0, lambda: self.set_status("✅ Command completed." if success else "⚠️ Command reported an error."))
        self.root.after(0, lambda: self.send_button.configure(state=tk.NORMAL))

    def _format_intermediate_steps(self, steps: List[Any]) -> str:
        """Format intermediate steps for display in GUI - pure presentation logic."""
        if not steps:
            return "🧠 No intermediate steps captured."

        lines: List[str] = []
        for idx, step in enumerate(steps, start=1):
            if isinstance(step, (list, tuple)) and len(step) == 2:
                action, observation = step
            else:
                action, observation = step, ""

            lines.append(f"🧠 Step {idx}")

            log_text = self.extract_action_log(action)
            if log_text:
                lines.append(f"   💭 {log_text.strip()}")

            tool_name = getattr(action, "tool", None)
            if tool_name:
                lines.append(f"   🔧 Action: {tool_name}")

            tool_input = getattr(action, "tool_input", None)
            if tool_input:
                lines.append(f"   📦 Input: {self.stringify(tool_input)}")

            if observation:
                lines.append(f"   👀 Observation: {self.stringify(observation)}")

            lines.append("")

        return "\n".join(lines).strip()

    def stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, indent=2, sort_keys=True)
        except (TypeError, ValueError):
            return str(value)

    def extract_action_log(self, action: Any) -> str:
        if action is None:
            return ""

        log_text = getattr(action, "log", None)
        if isinstance(log_text, str) and log_text.strip():
            return log_text

        message_log = getattr(action, "message_log", None)
        if message_log:
            parts: List[str] = []
            for message in message_log:
                content = getattr(message, "content", "")
                if isinstance(content, str) and content.strip():
                    parts.append(content.strip())
                elif content:
                    parts.append(str(content))
            if parts:
                return "\n".join(parts)

        if isinstance(action, str):
            return action

        tool_name = getattr(action, "tool", None)
        if tool_name:
            return f"Preparing to call tool '{tool_name}'"

        return ""

    # ------------------------------------------------------------------ #
    # Provider dialog
    # ------------------------------------------------------------------ #
    def open_provider_dialog(self) -> None:
        name = self.provider_var.get()
        config = self.provider_configs.get(name, {})

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Configure Provider - {name}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        for idx in range(0, 6):
            dialog.columnconfigure(idx % 2, weight=1 if idx % 2 == 1 else 0)

        ttk.Label(dialog, text="Provider Name:").grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        ttk.Label(dialog, text=name).grid(row=0, column=1, sticky="w", padx=10, pady=(10, 4))

        ttk.Label(dialog, text="Type:").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        type_var = tk.StringVar(value=config.get("type", "ollama"))
        type_combo = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=["ollama", "openai-compatible"],
            state="readonly",
            width=20,
        )
        type_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=4)

        ttk.Label(dialog, text="Base URL:").grid(row=2, column=0, sticky="w", padx=10, pady=4)
        base_var = tk.StringVar(value=config.get("base_url", ""))
        ttk.Entry(dialog, textvariable=base_var).grid(row=2, column=1, sticky="ew", padx=10, pady=4)

        ttk.Label(dialog, text="Default Model:").grid(row=3, column=0, sticky="w", padx=10, pady=4)
        default_model_var = tk.StringVar(value=config.get("default_model", ""))
        ttk.Entry(dialog, textvariable=default_model_var).grid(row=3, column=1, sticky="ew", padx=10, pady=4)

        ttk.Label(dialog, text="Default Models (comma separated):").grid(row=4, column=0, sticky="w", padx=10, pady=4)
        defaults_var = tk.StringVar(value=", ".join(config.get("default_models", [])))
        ttk.Entry(dialog, textvariable=defaults_var).grid(row=4, column=1, sticky="ew", padx=10, pady=4)

        requires_key_var = tk.BooleanVar(value=config.get("requires_api_key", False))
        ttk.Checkbutton(dialog, text="Requires API Key", variable=requires_key_var).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=10, pady=4
        )

        ttk.Label(dialog, text="API Key:").grid(row=6, column=0, sticky="w", padx=10, pady=4)
        api_key_var = tk.StringVar(value=config.get("api_key", ""))
        api_entry = ttk.Entry(dialog, textvariable=api_key_var, show="*", width=30)
        api_entry.grid(row=6, column=1, sticky="ew", padx=10, pady=4)

        def sync_api_state(*_):
            state = tk.NORMAL if requires_key_var.get() else tk.DISABLED
            api_entry.config(state=state)

        sync_api_state()
        requires_key_var.trace_add("write", sync_api_state)

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)

        def save():
            updated = {
                "type": type_var.get(),
                "base_url": base_var.get().strip(),
                "default_model": default_model_var.get().strip(),
                "default_models": [item.strip() for item in defaults_var.get().split(",") if item.strip()],
                "requires_api_key": requires_key_var.get(),
                "api_key": api_key_var.get().strip(),
            }
            self.provider_configs[name] = self.ensure_config_defaults(name, updated)
            if name == self.provider_var.get():
                self.on_provider_change()
            self.save_app_config()
            dialog.destroy()

        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ #
    # Voice input methods
    # ------------------------------------------------------------------ #
    def load_whisper_pipeline(self, selected_model=None, force_reload=False):
        """Load Whisper resources in a background thread to avoid blocking the UI."""
        if not (SPEECH_AVAILABLE and AUDIO_AVAILABLE and WHISPER_AVAILABLE):
            def on_fail_missing():
                self.loading_whisper = False
                self.voice_enabled = False
                self.pending_voice_start = False
                if hasattr(self, "voice_btn"):
                    self.voice_btn.config(text="🎤 Unavailable", state=tk.DISABLED)
                self.set_status("Voice recording unavailable (missing dependencies)")

            self.root.after(0, on_fail_missing)
            return
        if sr is None:
            def on_fail_sr():
                self.loading_whisper = False
                self.voice_enabled = False
                self.pending_voice_start = False
                if hasattr(self, "voice_btn"):
                    self.voice_btn.config(text="🎤 Unavailable", state=tk.DISABLED)
                self.set_status("Voice recording unavailable (speech_recognition missing)")

            self.root.after(0, on_fail_sr)
            return
        if selected_model is None:
            selected_model = self.whisper_model_var.get()

        if self.loading_whisper:
            if force_reload:
                self.pending_model_reload = selected_model
            return

        if self.voice_enabled and not force_reload and selected_model == self.current_whisper_model:
            return

        self.loading_whisper = True
        self.voice_enabled = False
        if hasattr(self, "voice_btn"):
            self.voice_btn.config(text="🎤 Loading..", state=tk.DISABLED)
        self.set_status(f"Loading Whisper {selected_model} model...")

        def loader():
            try:
                recognizer = self.recognizer or sr.Recognizer()

                recognizer.dynamic_energy_threshold = True
                recognizer.energy_threshold = 150
                recognizer.pause_threshold = 0.5
                recognizer.phrase_threshold = 0.1
                recognizer.non_speaking_duration = 0.2

                if WHISPER_AVAILABLE:
                    device = "cuda:0" if torch.cuda.is_available() else "cpu"
                    dtype = torch.float16 if torch.cuda.is_available() else torch.float32

                    if selected_model == "large":
                        model_path = "./whisper-large-v3-turbo"
                    elif selected_model == "medium":
                        model_path = "./whisper-medium"
                    else:
                        model_path = "./whisper-small"

                    if not os.path.exists(model_path):
                        raise FileNotFoundError(f"Whisper {selected_model} model not found at {model_path}")

                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        model_path,
                        dtype=dtype,
                        low_cpu_mem_usage=True,
                        use_safetensors=True
                    )
                    model.to(device)

                    processor = AutoProcessor.from_pretrained(model_path)
                    pipeline_obj = pipeline(
                        "automatic-speech-recognition",
                        model=model,
                        tokenizer=processor.tokenizer,
                        feature_extractor=processor.feature_extractor,
                        dtype=dtype,
                        device=device,
                        generate_kwargs={
                            "task": "transcribe",
                            "language": None  # Auto-detect language (English or Chinese)
                        }
                    )
                else:
                    model = None
                    processor = None
                    pipeline_obj = None
                    device = None
                    dtype = None

                def on_success():
                    self.recognizer = recognizer
                    self.whisper_model = model
                    self.whisper_processor = processor
                    self.whisper_pipeline = pipeline_obj
                    self.device = device
                    self.model_dtype = dtype
                    self.current_whisper_model = selected_model
                    self.voice_enabled = pipeline_obj is not None
                    self.loading_whisper = False
                    self.pending_model_reload = None
                    if hasattr(self, "voice_btn"):
                        if self.voice_enabled:
                            self.voice_btn.config(text="🎤 Record", state=tk.NORMAL)
                        else:
                            self.voice_btn.config(text="🎤 Disabled", state=tk.DISABLED)
                    if self.voice_enabled:
                        self.set_status(f"Whisper {selected_model} model ready")
                    else:
                        self.set_status("Whisper model unavailable")

                    if self.pending_model_reload and self.pending_model_reload != selected_model:
                        next_model = self.pending_model_reload
                        self.pending_model_reload = None
                        self.load_whisper_pipeline(selected_model=next_model, force_reload=True)
                        return

                    if getattr(self, "pending_voice_start", False):
                        if self.voice_enabled:
                            self.pending_voice_start = False
                            self.start_voice_input()
                        else:
                            self.pending_voice_start = False
                            messagebox.showwarning("Voice Recording", "Voice model is not available.")

                self.root.after(0, on_success)

            except Exception as e:
                def on_fail():
                    self.loading_whisper = False
                    self.voice_enabled = False
                    self.pending_model_reload = None
                    if hasattr(self, "voice_btn"):
                        label = "🎤 Disabled"
                        self.voice_btn.config(text=label, state=tk.DISABLED)
                    self.set_status(f"Model loading failed")
                    self.pending_voice_start = False
                    # messagebox.showerror("Model Loading Error", f"Failed to prepare voice model")

                self.root.after(0, on_fail)

        threading.Thread(target=loader, daemon=True).start()

    def toggle_voice_input(self):
        """Toggle voice recording on/off"""
        if not self.voice_enabled:
            messagebox.showwarning("Voice Recording", "Voice recording model is not ready yet. Please wait a moment and try again.")
            return

        if not self.is_listening:
            self.start_voice_input()
        else:
            self.finish_voice_input()

    def start_voice_input(self):
        """Start recording voice input"""
        if not self.voice_enabled:
            self.pending_voice_start = True
            if not self.loading_whisper:
                self.load_whisper_pipeline()
            self.create_voice_dialog(status_text="Loading voice model...", done_enabled=False)
            self.set_status("Preparing voice model...")
            return
        self.pending_voice_start = False
        if sr is None:
            messagebox.showwarning("Voice Recording", "speech_recognition library not available")
            return

        self.is_listening = True
        self.voice_btn.config(text="🎤 Recording...", state=tk.DISABLED)
        self.voice_transcribe_requested = False
        self.voice_stop_event = threading.Event()
        self.create_voice_dialog(status_text="🎤 Initializing microphone...", done_enabled=False)
        self.set_status("🎤 Recording active")

        thread = threading.Thread(target=self.begin_voice_capture, daemon=True)
        thread.start()
        self.voice_recording_thread = thread

    def finish_voice_input(self, event=None):
        if not self.is_listening:
            self.cancel_voice_input()
            return
        self.voice_transcribe_requested = True
        self.set_status("Processing recording...")
        self.update_voice_dialog("Processing...", False)
        self.disable_voice_dialog_buttons()
        self.stop_voice_recording()

    def cancel_voice_input(self, event=None):
        if not self.is_listening:
            if self.voice_dialog:
                self.voice_dialog.destroy()
                self.voice_dialog = None
            if self.voice_btn:
                self.voice_btn.config(text="🎤 Record", state=tk.NORMAL)
            self.set_status("Recording cancelled")
            self.pending_voice_start = False
            return
        self.voice_transcribe_requested = False
        self.set_status("Cancelling recording...")
        self.update_voice_dialog("Cancelling...", False)
        self.disable_voice_dialog_buttons()
        self.stop_voice_recording()

    def stop_voice_recording(self):
        if self.voice_stop_event:
            self.voice_stop_event.set()

    def create_voice_dialog(self, status_text="🎤 Recording...", done_enabled=True):
        """Create or refresh the voice input dialog."""
        self.voice_dialog = tk.Toplevel(self.root)
        self.voice_dialog.title("Voice Input")
        self.voice_dialog.geometry("320x120")
        self.voice_dialog.resizable(False, False)

        self.voice_dialog.transient(self.root)
        self.voice_dialog.grab_set()

        self.voice_status_label = ttk.Label(self.voice_dialog, text=status_text, font=('Arial', 14, 'bold'))
        self.voice_status_label.pack(pady=(20, 10))

        button_frame = ttk.Frame(self.voice_dialog)
        button_frame.pack(pady=(0, 15))

        self.voice_cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_voice_input)
        self.voice_cancel_btn.pack(side=tk.LEFT, padx=10)

        self.voice_done_btn = ttk.Button(button_frame, text="Done", command=self.finish_voice_input)
        self.voice_done_btn.pack(side=tk.LEFT, padx=10)
        if done_enabled:
            self.voice_done_btn.focus_set()
        else:
            self.voice_done_btn.config(state=tk.DISABLED)
            self.voice_cancel_btn.focus_set()

        self.voice_dialog.bind("<Return>", lambda e: self.finish_voice_input())
        self.voice_dialog.bind("<space>", lambda e: self.finish_voice_input())

        self.voice_dialog.protocol("WM_DELETE_WINDOW", self.cancel_voice_input)

    def update_voice_dialog(self, status_text=None, done_enabled=None):
        if status_text and self.voice_status_label:
            self.voice_status_label.config(text=status_text)
        if done_enabled is not None and self.voice_done_btn:
            self.voice_done_btn.config(state=tk.NORMAL if done_enabled else tk.DISABLED)
            if done_enabled:
                self.voice_done_btn.focus_set()
            else:
                if self.voice_cancel_btn:
                    self.voice_cancel_btn.focus_set()

    def disable_voice_dialog_buttons(self):
        if self.voice_cancel_btn:
            self.voice_cancel_btn.config(state=tk.DISABLED)
        if self.voice_done_btn:
            self.voice_done_btn.config(state=tk.DISABLED)

    def begin_voice_capture(self):
        microphone = None
        error_message = None
        try:
            microphone = sr.Microphone()
        except Exception as mic_error:
            error_message = f"Cannot access microphone: {mic_error}"

        if error_message or microphone is None:
            self.root.after(0, lambda: self.on_voice_session_complete("", error_message or "Microphone error", False))
            return

        self.root.after(0, lambda: self.update_voice_dialog("🎤 Listening...", True))
        self.record_voice_segment(microphone)

    def record_voice_segment(self, microphone):
        """Record a complete voice segment and then transcribe it"""
        if not self.voice_enabled or self.whisper_pipeline is None or self.recognizer is None:
            self.set_status("Voice model not ready")
            self.is_listening = False
            return

        sample_rate = getattr(microphone, "SAMPLE_RATE", 16000)
        sample_width = getattr(microphone, "SAMPLE_WIDTH", 2)
        chunk_size = getattr(microphone, "CHUNK", 1024)
        frames = []
        max_duration = 120  # safety guard
        start_time = time.time()
        transcribe_requested = False
        error_message = None
        text_result = ""

        try:
            with microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.05)
                stream = source.stream

                while not self.voice_stop_event.is_set() and (time.time() - start_time) < max_duration:
                    try:
                        data = stream.read(chunk_size)
                    except IOError as e:
                        # Handle buffer overflow errors gracefully
                        if e.errno == -9981:  # Input overflowed
                            continue
                        error_message = f"Recording error: {e}"
                        break
                    except Exception as read_error:
                        error_message = f"Recording error: {read_error}"
                        break

                    frames.append(data)

        except Exception as e:
            error_message = f"Voice recording error: {e}"

        transcribe_requested = self.voice_transcribe_requested

        if not frames:
            if not error_message:
                error_message = "No audio recorded"
        elif transcribe_requested and self.whisper_pipeline is None:
            error_message = "Voice model not ready"
        elif transcribe_requested and not error_message:
            audio_bytes = b"".join(frames)
            audio_data = sr.AudioData(audio_bytes, sample_rate, sample_width)

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_filename = tmp_file.name

            try:
                with open(tmp_filename, "wb") as f:
                    f.write(audio_data.get_wav_data())

                result = self.whisper_pipeline(
                    tmp_filename,
                    return_timestamps=False,
                    generate_kwargs={
                        "task": "transcribe",
                        "language": None  # Auto-detect between English and Chinese
                    }
                )
                text_result = result.get("text", "").strip()
            except Exception as transcribe_error:
                error_message = f"Transcription error: {transcribe_error}"
            finally:
                try:
                    os.unlink(tmp_filename)
                except OSError:
                    pass

        self.root.after(0, lambda: self.on_voice_session_complete(text_result, error_message, transcribe_requested))

    def on_voice_session_complete(self, text, error_message, transcribed):
        self.is_listening = False
        self.voice_stop_event = None
        self.voice_recording_thread = None
        self.voice_transcribe_requested = False

        if self.voice_dialog:
            try:
                self.voice_dialog.destroy()
            except tk.TclError:
                pass
            self.voice_dialog = None
        self.voice_status_label = None
        self.voice_cancel_btn = None
        self.voice_done_btn = None

        if self.voice_btn:
            self.voice_btn.config(text="🎤 Record", state=tk.NORMAL)

        if error_message:
            self.set_status("Recording error")
            self.append_chat("System", error_message)
            messagebox.showerror("Voice Recording", error_message)
        else:
            if transcribed and text:
                self.command_input.insert(tk.END, text + " ")
                snippet = text[:50] + ("..." if len(text) > 50 else "")
                self.set_status(f"Added: {snippet}")
            elif transcribed:
                self.set_status("No speech detected")
            else:
                self.set_status("Recording cancelled")

        self.root.after(1000, lambda: self.set_status("✅ Agent ready.") if self.agent else self.set_status("🛠️ Configure connection and initialize the agent."))

    # ------------------------------------------------------------------ #
    # Main loop entry
    # ------------------------------------------------------------------ #
def main() -> None:
    root = tk.Tk()
    app = UAVAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
