#!/usr/bin/env python3
"""
MultiUAV-Plat Control System - Task Template Manager

Manages task templates for quick task generation:
- Template storage and retrieval
- Template CRUD operations
- Built-in default templates
- Template instantiation with parameter substitution

Author: MultiUAV-Plat Control System
Version: Provided by application entrypoint
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
import copy
import time
from default_templates import DEFAULT_TEMPLATES
from template_placeholders import substitute_placeholders
from app_settings import DEFAULT_TEMPLATE_PATH

SUPPORTED_SESSION_TASK_TYPES = [
    'area_search',
    'area_assignment_and_patrol',
    'target_assignment',
    'target_tracking',
    'others',
]

TEMPLATE_SUITABLE_TASK_TYPES = ['all', *SUPPORTED_SESSION_TASK_TYPES]


class TaskTemplateManager:
    """Manager for task templates"""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template manager

        Args:
            template_dir: Directory to store templates. If None, uses default location.
        """
        if template_dir is None:
            # Use workspace-relative default location
            template_dir = os.path.abspath(DEFAULT_TEMPLATE_PATH)

        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.templates_file = self.template_dir / "task_templates.json"
        self.user_templates: Dict[str, Dict[str, Any]] = {}
        self.builtin_templates: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}

        # Load built-in templates (from code) and user templates (from disk)
        self.builtin_templates = {
            template_id: self.normalize_template_data(template_data)
            for template_id, template_data in copy.deepcopy(DEFAULT_TEMPLATES).items()
        }
        self.load_templates()

        # Compose combined view for runtime use
        self._compose_templates()

    def load_templates(self) -> bool:
        """Load user templates from file (built-ins are kept in code)

        Returns:
            True if templates loaded successfully, False otherwise
        """
        if not self.templates_file.exists():
            self.user_templates = {}
            self._compose_templates()
            return False

        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Only keep user-defined templates; skip any built-ins that might have been persisted
            self.user_templates = {}
            if isinstance(data, dict):
                for template_id, template_data in data.items():
                    if not isinstance(template_data, dict):
                        continue
                    if template_data.get('is_builtin'):
                        # Do not persist built-ins to disk; they come from default_templates.py
                        continue
                    template_copy = self.normalize_template_data(template_data)
                    template_copy['is_builtin'] = False
                    self.user_templates[template_id] = template_copy

            self._compose_templates()
            return True
        except Exception as e:
            print(f"Error loading templates: {e}")
            return False

    def save_templates(self) -> bool:
        """Save user templates to file (built-ins stay in code)

        Returns:
            True if templates saved successfully, False otherwise
        """
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_templates, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving templates: {e}")
            return False

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID

        Args:
            template_id: Template identifier

        Returns:
            Template data or None if not found
        """
        return self.templates.get(template_id)

    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get all templates

        Returns:
            Dictionary of all templates
        """
        return copy.deepcopy(self.templates)

    def get_template_list(self) -> List[Dict[str, Any]]:
        """Get list of templates with metadata

        Returns:
            List of template metadata dicts
        """
        result = []
        for template_id, template_data in self.templates.items():
            result.append({
                'id': template_id,
                'name': template_data.get('name', template_id),
                'description': template_data.get('description', ''),
                'category': template_data.get('category', 'Custom'),
                'difficulty': template_data.get('difficulty', 'medium'),
                'api_count': len(template_data.get('related_apis', [])),
                'check_count': self.count_execution_checks(template_data.get('execution_check_apis')),
                'suitable_task': copy.deepcopy(template_data.get('suitable_task', [])),
                'exclude_in_random_generation': bool(template_data.get('exclude_in_random_generation', False)),
                'is_builtin': template_data.get('is_builtin', False),
                'created_at': template_data.get('created_at', 0),
                'last_modified': template_data.get('last_modified', 0)
            })
        return result

    @staticmethod
    def count_execution_checks(execution_check_apis: Any) -> int:
        """Count leaf execution checks, excluding nested logic groups."""
        if not isinstance(execution_check_apis, dict):
            return 0

        checks = execution_check_apis.get('checks')
        if isinstance(checks, list):
            return sum(TaskTemplateManager.count_execution_checks(child) for child in checks)

        return 1 if execution_check_apis.get('endpoint') else 0

    @staticmethod
    def normalize_suitable_task(raw_value: Any) -> List[str]:
        """Normalize suitable task metadata to a deduplicated list of valid task types."""
        if raw_value in (None, '', []):
            return []

        if isinstance(raw_value, str):
            candidates = [raw_value]
        elif isinstance(raw_value, (list, tuple, set)):
            candidates = list(raw_value)
        else:
            return []

        normalized: List[str] = []
        seen = set()
        for value in candidates:
            if not isinstance(value, str):
                continue
            task_type = value.strip()
            if task_type == 'all':
                return ['all']
            if task_type in SUPPORTED_SESSION_TASK_TYPES and task_type not in seen:
                seen.add(task_type)
                normalized.append(task_type)
        return normalized

    @classmethod
    def normalize_template_data(cls, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize template metadata for runtime use and persistence."""
        normalized = copy.deepcopy(template_data)
        normalized['suitable_task'] = cls.normalize_suitable_task(
            normalized.get('suitable_task')
        )
        normalized['exclude_in_random_generation'] = bool(
            normalized.get('exclude_in_random_generation', False)
        )
        return normalized

    def add_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """Add or update a template

        Args:
            template_id: Template identifier
            template_data: Template data

        Returns:
            True if template added successfully
        """
        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")

        # Make a deep copy to avoid modifying the original
        template_copy = self.normalize_template_data(template_data)

        current_time = time.time()

        # Check if this is an update or a new template
        if template_id in self.user_templates:
            # Update: preserve created_at, update last_modified
            existing_template = self.user_templates[template_id]
            template_copy['created_at'] = existing_template.get('created_at', current_time)
            template_copy['last_modified'] = current_time
        else:
            # New template: set both created_at and last_modified
            template_copy['created_at'] = current_time
            template_copy['last_modified'] = current_time

        template_copy['is_builtin'] = False
        self.user_templates[template_id] = template_copy
        self._compose_templates()
        return self.save_templates()

    def delete_template(self, template_id: str) -> bool:
        """Delete a template

        Args:
            template_id: Template identifier

        Returns:
            True if template deleted successfully
        """
        if template_id not in self.templates:
            return False

        # Don't allow deleting built-in templates
        if self.templates[template_id].get('is_builtin', False):
            raise ValueError("Cannot delete built-in templates")

        del self.user_templates[template_id]
        self._compose_templates()
        return self.save_templates()

    def instantiate_template(self, template_id: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a task from a template with parameter substitution

        Args:
            template_id: Template identifier
            parameters: Optional parameters to substitute in template

        Returns:
            Task data ready for creation, or None if template not found
        """
        template = self.get_template(template_id)
        if not template:
            return None

        template_name = template.get('name') or template_id
        template_creator = template.get('creator') or 'Unknown'
        origin_descriptor = f"Task Template {template_name} created by {template_creator}"

        # Create a deep copy of the template
        task_data = copy.deepcopy(template)

        # Remove template metadata
        task_data.pop('is_builtin', None)
        task_data.pop('category', None)
        task_data.pop('template_description', None)
        task_data.pop('suitable_task', None)
        task_data.pop('exclude_in_random_generation', None)
        task_data['originated_from'] = origin_descriptor

        # Apply parameter substitutions if provided
        if parameters:
            task_data = self._apply_parameters(task_data, parameters)

        # Preserve the origin descriptor even if parameters didn't touch it
        task_data.setdefault('originated_from', origin_descriptor)

        return task_data

    def _compose_templates(self) -> None:
        """Rebuild the combined template map from built-in + user templates."""
        combined: Dict[str, Dict[str, Any]] = copy.deepcopy(self.builtin_templates)
        for template_id, template_data in self.user_templates.items():
            combined[template_id] = copy.deepcopy(template_data)
        self.templates = combined

    def _apply_parameters(self, task_data: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply parameter substitutions to task data

        Supports:
        - Direct field replacement (e.g., name, description)
        - Nested field replacement in APIs (e.g., drone_id in related_apis)
        - Comprehensive placeholder replacement in content and content_aliases
        - All placeholders from template_placeholders module
        - Multi-entity indexed placeholders (e.g., {drone_1_id}, {drone_2_id})
        - Sticky random values (same random placeholder = same value across task)

        Args:
            task_data: Task data with placeholders
            parameters: Parameter values

        Returns:
            Task data with parameters applied
        """
        # Simple field replacements
        for key in ['name', 'description', 'creator', 'difficulty']:
            if key in parameters and key in task_data:
                task_data[key] = parameters[key]

        # Use sticky random values - generate random values once and reuse
        # This ensures {random_altitude} gives the same value in content, aliases, and APIs
        random_cache = {}

        # Replace ALL placeholders in content field using comprehensive substitution
        if 'content' in task_data and isinstance(task_data['content'], str):
            task_data['content'], random_cache = substitute_placeholders(
                task_data['content'], parameters, random_cache
            )

        # Replace ALL placeholders in content_aliases using same random cache
        if 'content_aliases' in task_data and isinstance(task_data['content_aliases'], list):
            new_aliases = []
            for alias in task_data['content_aliases']:
                if isinstance(alias, str):
                    substituted_alias, random_cache = substitute_placeholders(alias, parameters, random_cache)
                    new_aliases.append(substituted_alias)
                else:
                    new_aliases.append(alias)
            task_data['content_aliases'] = new_aliases

        def _substitute_value(value: Any) -> Any:
            nonlocal random_cache

            if isinstance(value, dict):
                substituted_dict = {}
                for key, child_value in value.items():
                    if key in parameters and not (
                        isinstance(child_value, str)
                        and child_value.startswith('{')
                        and child_value.endswith('}')
                    ):
                        substituted_dict[key] = parameters[key]
                    else:
                        substituted_dict[key] = _substitute_value(child_value)
                return substituted_dict
            if isinstance(value, list):
                return [_substitute_value(child_value) for child_value in value]
            if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
                placeholder_key = value[1:-1]
                if placeholder_key in parameters:
                    return parameters[placeholder_key]
                if placeholder_key in random_cache:
                    return random_cache[placeholder_key]

                substituted, random_cache = substitute_placeholders(value, parameters, random_cache)
                try:
                    return float(substituted)
                except ValueError:
                    return substituted
            return value

        # Replace parameters in related_apis using same random cache
        if 'related_apis' in task_data:
            for api in task_data['related_apis']:
                if 'parameters' in api:
                    api['parameters'] = _substitute_value(api['parameters'])

        # Replace parameters in execution_check_apis using same random cache
        def _replace_checks(node: Dict[str, Any]):
            nonlocal random_cache

            def _coerce_expect(expect_val: Any) -> Optional[bool]:
                """Normalize expect values to booleans when possible."""
                if isinstance(expect_val, bool):
                    return expect_val
                if isinstance(expect_val, dict) and 'result' in expect_val:
                    return bool(expect_val.get('result'))
                if isinstance(expect_val, str):
                    lowered = expect_val.strip().lower()
                    if lowered in ('true', 'false'):
                        return lowered == 'true'
                return None

            if not isinstance(node, dict):
                return
            if 'checks' in node:
                for child in node.get('checks', []):
                    _replace_checks(child)
            else:
                params = node.get('parameters', {})
                node['parameters'] = _substitute_value(params)

                expect_val = node.get('expect')
                expect_bool: Optional[bool] = None
                if isinstance(expect_val, str) and expect_val.startswith('{') and expect_val.endswith('}'):
                    placeholder_key = expect_val[1:-1]
                    if placeholder_key in parameters:
                        expect_bool = _coerce_expect(parameters[placeholder_key])
                    elif placeholder_key in random_cache:
                        expect_bool = _coerce_expect(random_cache[placeholder_key])
                    else:
                        substituted, random_cache = substitute_placeholders(expect_val, parameters, random_cache)
                        expect_bool = _coerce_expect(substituted)
                else:
                    expect_bool = _coerce_expect(expect_val)

                if expect_bool is not None:
                    node['expect'] = expect_bool
                elif 'expect' in node:
                    node.pop('expect', None)

        if 'execution_check_apis' in task_data:
            _replace_checks(task_data['execution_check_apis'])

        return task_data
