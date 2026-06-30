"""
Parsing Error Template

This template defines the error message shown to the LLM when it produces
invalid JSON in the Action Input field.
"""

PARSING_ERROR_TEMPLATE = """Parsing error: {error}

REMINDER - Action Input must be valid JSON:
- Use double quotes for keys and string values
- Use curly braces: {{}}
- For no parameters: {{}}
- For one parameter: {{"drone_id": "drone-001"}}
- For multiple parameters: {{"drone_id": "drone-001", "altitude": 15.0}}
- Numbers WITHOUT quotes, strings WITH quotes

Please try again with proper JSON format."""
