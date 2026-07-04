#!/usr/bin/env python3
"""
MultiUAV-Plat Server System - Main Entry Point

Copyright (C) 2026 MultiUAV-Plat Server System Project

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
# Suppress pygame greeting message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import warnings
# Suppress pkg_resources deprecation warning from dependencies
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated as an API.*")

import sys
import argparse
import threading
import uvicorn
import time
import logging

import subprocess
from config.logging_config import setup_logging
from api.server import (app, drone_controller, target_controller, obstacle_controller,
                        environment_controller, session_controller)
from ui.interface import start_ui, DroneUI
from models.session import DEFAULT_REQUEST_HISTORY_LIMIT

# Version configuration
VERSION = "0.4.1"


def positive_int(value: str) -> int:
    """Parse a strictly positive integer for command-line configuration."""
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed_value


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the application argument parser."""
    parser = argparse.ArgumentParser(description="Drone Control System")
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only the API server without UI"
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Run only the UI without API server"
    )
    parser.add_argument(
        "--ui-drone-control",
        action="store_true",
        help="Enable UI drone control buttons and map-click movement"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="API server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )
    parser.add_argument(
        "--request-history-limit",
        type=positive_int,
        default=DEFAULT_REQUEST_HISTORY_LIMIT,
        help=(
            "Maximum request-history records retained for the current session "
            f"(default: {DEFAULT_REQUEST_HISTORY_LIMIT})"
        ),
    )
    parser.add_argument(
        "--dialog",
        action="store_true",
        help="Internal use: Run startup dialog"
    )
    return parser


def start_api_server(host: str, port: int):
    """Start the FastAPI server in a separate thread"""
    # Configure logging format to include datetime with colors
    log_config = uvicorn.config.LOGGING_CONFIG

    # Use 'default' formatter class for colorized output
    log_config["formatters"]["default"] = {
        "()": "uvicorn.logging.DefaultFormatter",
        "fmt": "%(levelprefix)s %(asctime)s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "use_colors": True
    }

    log_config["formatters"]["access"] = {
        "()": "uvicorn.logging.AccessFormatter",
        "fmt": '%(levelprefix)s %(asctime)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
        "datefmt": "%Y-%m-%d %H:%M:%S",
        "use_colors": True
    }

    uvicorn.run(app, host=host, port=port, log_config=log_config, access_log=False)


def ask_show_ui():
    """Run the startup dialog in a separate process."""
    try:
        if getattr(sys, 'frozen', False):
            # If frozen (Pyinstaller), run the executable itself with --dialog flag
            cmd = [sys.executable, "--dialog"]
        else:
            # If running from source, run ui/dialog.py as a separate process
            script_path = os.path.join(os.path.dirname(__file__), "ui", "dialog.py")
            cmd = [sys.executable, script_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        output = result.stdout.strip()
        if "YES" in output:
            return True
        elif "NO" in output:
            return False
        else:
            return None
    except Exception as e:
        print(f"Error showing startup dialog: {e}")
        return None


def start_simulation():
    """Run simulation updates for targets and environment"""
    while True:
        # Update moving targets
        target_controller.update_moving_targets()
        session_controller.sync_current_session_state()

        # Simulate gradual weather changes
        environment_controller.simulate_weather_changes()

        # Sleep to control update frequency
        time.sleep(1.0)  # Update every second


def print_banner():
    """Print welcome banner for the server"""
    # Calculate padding to keep banner aligned
    version_line = f"MultiUAV-Plat Server System v{VERSION}"
    padding = (70 - len(version_line)) // 2
    version_formatted = " " * padding + version_line

    banner = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║{version_formatted:<70}║
║              Multi-Drone Coordinative Planning Platform              ║
║                                                                      ║
║             © 2026 MultiUAV-Plat Server System Project               ║
║                     Licensed under GNU GPL v3                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝


"""
    print(banner, flush=True)


def run_headless_server_loop(stop_event: threading.Event, logger: logging.Logger):
    """Keep the main thread alive while API server runs in daemon thread."""
    logger.info("API server running in background. Press Ctrl+C to stop.")
    sys.stdout.flush()
    try:
        # On Windows, wait() without a timeout can block signals.
        # We use a loop with a timeout to allow KeyboardInterrupt to be caught.
        while not stop_event.is_set():
            stop_event.wait(1.0)
    except KeyboardInterrupt:
        logger.info("Shutting down MultiUAV-Plat Server System...")
        logger.info("Goodbye!")


def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    # Handle dialog mode (used for subprocess in Pyinstaller/frozen app)
    # MUST be done before any print/logging to avoid polluting stdout
    if args.dialog:
        try:
            from ui.dialog import show_startup_dialog
            show_startup_dialog()
        except ImportError:
            # Fallback if ui.dialog cannot be imported directly (should not happen if bundled)
            print("CANCEL")
        return

    # Print welcome banner
    print_banner()

    # Initialize logging system
    setup_logging()

    # Get logger for main application
    logger = logging.getLogger("uav_system")
    session_controller.set_request_history_limit(args.request_history_limit)
    logger.info(
        "Request history retention: "
        f"{args.request_history_limit} records for the current session"
    )
    
    # Start the simulation thread for targets and environment
    sim_thread = threading.Thread(
        target=start_simulation,
        daemon=True
    )
    sim_thread.start()
    
    if args.api_only:
        # Run only the API server
        logger.info(f"Starting API server at http://{args.host}:{args.port}")
        logger.info(f"API Documentation: http://{args.host}:{args.port}/docs")
        start_api_server(args.host, args.port)
    elif args.ui:
        # Run only the UI with its own controllers
        logger.info("Starting UI interface...")
        start_ui(
            ui_drone_control=args.ui_drone_control,
            request_history_limit=args.request_history_limit,
        )
    else:
        # No flags provided - start API server in background and ask user about UI
        # Use an event to signal when to stop the main thread
        stop_event = threading.Event()

        logger.info(f"Starting API server at http://{args.host}:{args.port}")
        logger.info(f"API Documentation: http://{args.host}:{args.port}/docs")

        api_thread = threading.Thread(
            target=start_api_server,
            args=(args.host, args.port),
            daemon=True
        )
        api_thread.start()

        # Give API server a moment to start
        time.sleep(0.5)

        # Show graphical dialog asking if user wants UI (runs on main thread)
        show_ui = ask_show_ui()

        if show_ui is None:
            # Handle close button (X) on dialog as no
            logger.info("Operation cancelled by user. Exiting...")
            sys.exit(0)
            
        if not show_ui:
            # If user selected "No", but just closed the dialog window (result=False),
            # we should also just exit or stay in CLI mode?
            # The prompt asks "Start UI?", so "No" means run API only.
            # But earlier user requested "when the server/terminal is closed the UI should also be closed"
            # And implicit "if I say No, I might want to just run the server".
            # Let's assume "No" means "Run Server headless".
            pass

        if show_ui:
            logger.info("Starting UI interface...")
            # Start the UI in the main thread with shared controllers
            ui = DroneUI(
                drone_controller=drone_controller,
                target_controller=target_controller,
                obstacle_controller=obstacle_controller,
                environment_controller=environment_controller,
                session_controller=session_controller,
                confirm_on_close=True,
                ui_drone_control=args.ui_drone_control,
                request_history_limit=args.request_history_limit,
            )
            close_action = "close_server"
            try:
                close_action = ui.run()
            except KeyboardInterrupt:
                logger.info("\nStopping UI and Server...")
            finally:
                if close_action == "close_ui_only":
                    # Small delay to let macOS fully dismiss the pygame window.
                    time.sleep(0.2)
                    run_headless_server_loop(stop_event, logger)
                else:
                    logger.info("Goodbye!")
        else:
            run_headless_server_loop(stop_event, logger)


if __name__ == "__main__":
    main()
