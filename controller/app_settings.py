"""
Shared application settings module.

Manages all application settings in a single unified settings.json file.
"""

import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, Any, Optional, Callable

# Default settings file location (in user's home directory)
SETTINGS_FILE = Path('./settings.json')

# Default storage path for session files
DEFAULT_STORAGE_PATH = str('./UAVSessions')
# Default storage path for templates (workspace relative)
DEFAULT_TEMPLATE_PATH = str('./templates')
# Default ADMIN API key used when settings leave the API key blank.
DEFAULT_API_KEY = "admin_key_for_the_controller_only_12"

# Default settings
DEFAULT_SETTINGS = {
    'username': 'SYSTEM',
    'session_storage_path': DEFAULT_STORAGE_PATH,
    'template_storage_path': DEFAULT_TEMPLATE_PATH,
    'api_base_url': 'http://127.0.0.1:8000',
    'agent_base_url': 'http://localhost:18000',
    'api_key': None,
}


class AppSettings:
    """Application settings manager"""

    def __init__(self):
        self.settings = self.load()

    def load(self) -> Dict[str, Any]:
        """Load settings from file, creating with defaults if doesn't exist"""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new settings
                    return {**DEFAULT_SETTINGS, **loaded}
            else:
                # Create default settings file
                self.save(DEFAULT_SETTINGS)
                return dict(DEFAULT_SETTINGS)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return dict(DEFAULT_SETTINGS)

    def save(self, settings: Optional[Dict[str, Any]] = None) -> bool:
        """Save settings to file"""
        if settings is not None:
            self.settings = settings

        try:
            # Ensure directory exists
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default=None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a setting value and save"""
        self.settings[key] = value
        return self.save()

    def update(self, updates: Dict[str, Any]) -> bool:
        """Update multiple settings at once"""
        self.settings.update(updates)
        return self.save()


# Singleton instance
_settings_instance: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Get the singleton settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = AppSettings()
    return _settings_instance


def resolve_api_key(api_key: Optional[str]) -> str:
    """Return the configured API key, or the built-in ADMIN key when blank."""
    if api_key and str(api_key).strip():
        return str(api_key).strip()
    return DEFAULT_API_KEY


class SettingsDialog:
    """Dialog for editing application settings."""

    def __init__(self, parent, on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.parent = parent
        self.on_save_callback = on_save_callback
        self.app_settings = get_settings()
        self.logger = logging.getLogger('SettingsDialog')

        # Defer import to avoid circular dependency
        from utils import set_window_geometry_and_center, sanitize_filename

        self.dialog = tk.Toplevel(parent)
        try:
            # Try to set icon if parent has one
            icon = getattr(parent, "_uav_icon_image", None)
            if icon:
                self.dialog.iconphoto(False, icon)
        except Exception:
            pass
            
        self.dialog.title("Settings")
        set_window_geometry_and_center(self.dialog, 640, 560, parent)

        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # === User Profile Section ===
        ttk.Label(main_frame, text="User Profile",
                  font=('Arial', 10, 'bold')).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="Default Username:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.username_var = tk.StringVar(value=self.app_settings.get('username', 'SYSTEM'))
        username_entry = ttk.Entry(main_frame, textvariable=self.username_var, width=40)
        username_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(
            main_frame,
            text="Used as the default creator for sessions and tasks.",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))

        # === Session Storage Section ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(main_frame, text="Session Storage",
                  font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="Storage Path:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.storage_path_var = tk.StringVar(value=self.app_settings.get('session_storage_path') or DEFAULT_STORAGE_PATH)
        storage_entry = ttk.Entry(main_frame, textvariable=self.storage_path_var, width=40, state='readonly')
        storage_entry.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Button(main_frame, text="Browse...", command=self.browse_storage).grid(row=6, column=2, padx=(5, 0), pady=5)

        ttk.Label(
            main_frame,
            text="Folder where session files are stored for import/export.",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=7, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))

        # Template storage section
        ttk.Label(main_frame, text="Template Storage",
                  font=('Arial', 10, 'bold')).grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="Storage Path:").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.template_path_var = tk.StringVar(value=self.app_settings.get('template_storage_path') or DEFAULT_TEMPLATE_PATH)
        template_entry = ttk.Entry(main_frame, textvariable=self.template_path_var, width=40, state='readonly')
        template_entry.grid(row=9, column=1, sticky=(tk.W, tk.E), pady=5)

        ttk.Button(main_frame, text="Browse...", command=self.browse_template_storage).grid(row=9, column=2, padx=(5, 0), pady=5)

        ttk.Label(
            main_frame,
            text="Folder where task templates are stored (task_templates.json).",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=10, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))

        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # === API Configuration Section ===
        ttk.Label(main_frame, text="API Configuration",
                  font=('Arial', 10, 'bold')).grid(row=12, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="UAV API Base URL:").grid(row=13, column=0, sticky=tk.W, pady=5)
        self.api_base_url_var = tk.StringVar(value=self.app_settings.get('api_base_url', 'http://127.0.0.1:8000'))
        ttk.Entry(main_frame, textvariable=self.api_base_url_var, width=40).grid(
            row=13, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )

        ttk.Label(
            main_frame,
            text="Base URL for the UAV API server used by Session Manager, GUI Controller, and Batch Check.",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=14, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))

        ttk.Label(main_frame, text="Agent API Base URL:").grid(row=15, column=0, sticky=tk.W, pady=5)
        self.agent_base_url_var = tk.StringVar(value=self.app_settings.get('agent_base_url', 'http://localhost:18000'))
        ttk.Entry(main_frame, textvariable=self.agent_base_url_var, width=40).grid(
            row=15, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )

        ttk.Label(
            main_frame,
            text="Base URL for the agent server used by Batch Check.",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=16, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))

        # API Secret Key
        ttk.Label(main_frame, text="API Secret Key:").grid(row=17, column=0, sticky=tk.W, pady=5)
        current_setting_key = self.app_settings.get('api_key', '')
        self.api_key_var = tk.StringVar(value=current_setting_key if current_setting_key else "")
        self.api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.grid(row=17, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Show/Hide checkbox
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Show", variable=self.show_key_var, command=self.toggle_key_visibility).grid(row=17, column=2, padx=5, sticky=tk.W)

        ttk.Label(
            main_frame,
            text="Key for authenticating with the API server (Leave blank for built-in ADMIN role).",
            font=('Arial', 9),
            foreground='gray'
        ).grid(row=18, column=1, columnspan=2, sticky=tk.W, pady=(0, 5))
        

        ttk.Button(main_frame, text="Save Settings", command=self.save_settings).grid(
            row=19, column=0, columnspan=3, pady=10)

        main_frame.columnconfigure(1, weight=1)
        username_entry.focus_set()

    def browse_storage(self):
        current = self.storage_path_var.get()
        selected = filedialog.askdirectory(
            title="Select Session Storage Folder",
            initialdir=current,
            parent=self.dialog
        )
        if selected:
            self.storage_path_var.set(selected)

    def browse_template_storage(self):
        current = self.template_path_var.get()
        selected = filedialog.askdirectory(
            title="Select Template Storage Folder",
            initialdir=current,
            parent=self.dialog
        )
        if selected:
            self.template_path_var.set(selected)

    def toggle_key_visibility(self):
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def save_settings(self):
        new_username = self.username_var.get().strip()
        if not new_username:
            messagebox.showwarning("Invalid Input", "Username cannot be empty", parent=self.dialog)
            return
        
        new_api_key = self.api_key_var.get().strip()

        updated = dict(self.app_settings.settings)
        updated['username'] = new_username
        updated['session_storage_path'] = self.storage_path_var.get() or DEFAULT_STORAGE_PATH
        updated['template_storage_path'] = self.template_path_var.get() or DEFAULT_TEMPLATE_PATH
        updated['api_base_url'] = self.api_base_url_var.get().strip() or 'http://127.0.0.1:8000'
        updated['agent_base_url'] = self.agent_base_url_var.get().strip() or 'http://localhost:18000'
        
        # Save API key if provided, otherwise save as None so the default ADMIN key is used.
        updated['api_key'] = new_api_key if new_api_key else None

        if self.app_settings.save(updated):
            self.logger.info(f"Settings updated. Username: {new_username}")
            
            if self.on_save_callback:
                self.on_save_callback(updated)
            
            messagebox.showinfo("Settings Saved", "User settings saved successfully.", parent=self.dialog)
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", "Failed to save user settings", parent=self.dialog)

    def wait_window(self):
        self.dialog.wait_window()


def show_settings_dialog(parent, on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
    """Show the settings dialog."""
    dialog = SettingsDialog(parent, on_save_callback)
    dialog.wait_window()
