#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Main Entry Point

This is the main entry point for the MultiUAV-Plat Control System.
It starts with the Session Manager, allowing users to:
- Create, load, and manage sessions
- Export/import session data
- Launch the GUI controller for selected sessions

Author: MultiUAV-Plat Control System
Version: See VERSION constant below
"""

import sys
import os
import json
import traceback
import importlib
import os
# Suppress pygame greeting message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_version import VERSION, BUILD
from session_manager import SessionManager

SESSION_EDITOR_IMPORT_ERROR = None
start_session_editor = None
try:
    start_session_editor = importlib.import_module("session_editor").start_session_editor
except ImportError as exc:
    SESSION_EDITOR_IMPORT_ERROR = exc


def run_session_editor_from_config(config_file: str) -> None:
    """Launch the session editor using the provided temp config file."""
    if not config_file:
        raise ValueError("Config file path is required")

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with open(config_file, 'r') as f:
        config = json.load(f)

    try:
        os.unlink(config_file)
    except Exception as e:
        print(f"Warning: Could not delete temp config file: {e}", file=sys.stderr)

    session_id = config.get('session_id')
    session_data = config.get('session_data')
    save_signal_file = config.get('save_signal_file')

    if not session_id or not session_data:
        raise ValueError("Invalid configuration - missing session_id or session_data")

    if start_session_editor is None:
        raise RuntimeError(
            "Failed to import session editor. Ensure pygame (and other dependencies) are installed."
        ) from SESSION_EDITOR_IMPORT_ERROR

    print(f"Starting session editor for: {session_data.get('name', session_id)}")

    start_session_editor(
        session_id=session_id,
        session_data=session_data,
        save_signal_file=save_signal_file
    )

    print("Session editor closed normally")


def main():
    """
    Main entry point for the MultiUAV-Plat Control System.
    Starts the Session Manager interface.
    """
    if len(sys.argv) > 1 and sys.argv[1] == '--launch-session-editor':
        config_path = sys.argv[2] if len(sys.argv) > 2 else None
        if not config_path:
            print("Error: Missing config file path for session editor launch", file=sys.stderr)
            sys.exit(1)

        try:
            run_session_editor_from_config(config_path)
        except Exception as e:
            print(f"Error starting session editor: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

        sys.exit(0)

    try:
        # Create and run session manager
        session_manager = SessionManager(version=VERSION, build=BUILD)
        session_manager.run()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting MultiUAV-Plat Control System: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
