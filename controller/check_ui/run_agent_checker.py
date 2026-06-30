#!/usr/bin/env python3
"""
Launcher script for AI Agent Auto-Check UI

Run this script to start the AI Agent Auto-Check application.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the application
from check_ui.agent_checker import main

if __name__ == '__main__':
    print("Starting AI Agent Auto-Check...")
    print("Please ensure:")
    print("  1. API server is running on port 8000")
    print("  2. Agent server is running on port 18000")
    print()
    main()
