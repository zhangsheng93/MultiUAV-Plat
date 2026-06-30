import unittest
import json
import os
import tempfile
from pathlib import Path
from app_settings import AppSettings, DEFAULT_API_KEY, DEFAULT_SETTINGS, resolve_api_key

class TestAppSettings(unittest.TestCase):

    def setUp(self):
        # Create a temporary file for settings
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.settings_path = Path(self.temp_file.name)
        
        # Patch the SETTINGS_FILE in app_settings module
        # Since we can't easily patch the global variable in the module for the class instance,
        # we'll check if we can inject it or we have to rely on the fact that AppSettings 
        # loads from a file.
        
        # AppSettings uses a hardcoded SETTINGS_FILE global. 
        # To test it properly without modifying the code, we might need to mock os.path.exists 
        # and open, or just accept we are testing the logic but pointing to a temp file is hard 
        # without dependency injection.
        
        # However, looking at the code:
        # SETTINGS_FILE = Path('./settings.json')
        # ...
        # class AppSettings:
        #    def __init__(self):
        #        self.settings = self.load()
        
        pass

    def tearDown(self):
        if self.settings_path.exists():
            os.unlink(self.settings_path)

    def test_default_settings(self):
        # Test that defaults are loaded when no file exists
        # We can simulate this by instantiating AppSettings and checking values
        # assuming the real settings.json might exist or not. 
        # This is flaky if we run in a real env.
        
        # Instead, let's test the dictionary operations which are pure logic
        app_settings = AppSettings()
        # Reset to defaults for testing
        app_settings.settings = dict(DEFAULT_SETTINGS)
        
        self.assertEqual(app_settings.get('username'), 'SYSTEM')
        self.assertIsNone(app_settings.get('non_existent'))
        self.assertEqual(app_settings.get('non_existent', 'default'), 'default')

    def test_update_settings(self):
        app_settings = AppSettings()
        # Mock the save method to avoid writing to the real file
        original_save = app_settings.save
        app_settings.save = lambda x=None: True
        
        app_settings.set('username', 'TestUser')
        self.assertEqual(app_settings.get('username'), 'TestUser')
        
        app_settings.update({'api_key': 'secret'})
        self.assertEqual(app_settings.get('api_key'), 'secret')
        
        # Restore save
        app_settings.save = original_save

    def test_resolve_api_key_uses_default_for_blank_values(self):
        self.assertEqual(resolve_api_key(None), DEFAULT_API_KEY)
        self.assertEqual(resolve_api_key(''), DEFAULT_API_KEY)
        self.assertEqual(resolve_api_key('   '), DEFAULT_API_KEY)

    def test_resolve_api_key_uses_user_input_when_present(self):
        self.assertEqual(resolve_api_key('custom_admin_key'), 'custom_admin_key')
        self.assertEqual(resolve_api_key('  custom_admin_key  '), 'custom_admin_key')

if __name__ == '__main__':
    unittest.main()
