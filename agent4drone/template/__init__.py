"""
UAV Agent Templates

This package contains prompt templates for the UAV control agent.
"""

from .agent_prompt import AGENT_PROMPT
from .parsing_error import PARSING_ERROR_TEMPLATE
from .system_prompt import SYSTEM_PROMPT_TEMPLATE, build_system_prompt

__all__ = [
    "AGENT_PROMPT",
    "PARSING_ERROR_TEMPLATE",
    "SYSTEM_PROMPT_TEMPLATE",
    "build_system_prompt",
]
