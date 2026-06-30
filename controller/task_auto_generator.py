"""Shared template-based automatic task generation helpers."""

from dataclasses import dataclass
import random
from typing import Any, Dict, List, Optional

from template_placeholders import find_placeholders_in_text
from utils import create_new_name


@dataclass
class AutoTaskGenerationResult:
    requested_count: int
    created_count: int
    suitable_template_count: int
    compatible_template_count: int
    reason: Optional[str] = None


def template_matches_task_type(template_manager, template_data: Dict[str, Any], session_task_type: str) -> bool:
    suitable = template_manager.normalize_suitable_task(template_data.get('suitable_task'))
    return not suitable or 'all' in suitable or session_task_type in suitable


def detect_template_entity_groups(template_data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    placeholders = set()

    def collect_from_value(value: Any):
        if isinstance(value, str):
            placeholders.update(find_placeholders_in_text(value))
        elif isinstance(value, dict):
            for nested in value.values():
                collect_from_value(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_from_value(nested)

    collect_from_value(template_data.get('content', ''))
    collect_from_value(template_data.get('content_aliases', []))
    collect_from_value(template_data.get('related_apis', []))
    collect_from_value(template_data.get('execution_check_apis', {}))

    groups: Dict[str, Dict[str, Optional[str]]] = {}
    for placeholder in placeholders:
        if placeholder.endswith('_id'):
            base_name = placeholder[:-3]
            entity_type = base_name.split('_')[0]
            if entity_type in {'drone', 'target', 'obstacle'}:
                groups.setdefault(base_name, {
                    'base_name': base_name,
                    'entity_type': entity_type,
                    'id_param': None,
                    'name_param': None,
                })
                groups[base_name]['id_param'] = placeholder
        elif placeholder.endswith('_name'):
            base_name = placeholder[:-5]
            entity_type = base_name.split('_')[0]
            if entity_type in {'drone', 'target', 'obstacle'}:
                groups.setdefault(base_name, {
                    'base_name': base_name,
                    'entity_type': entity_type,
                    'id_param': None,
                    'name_param': None,
                })
                groups[base_name]['name_param'] = placeholder

    return list(groups.values())


def build_auto_template_params(
    template_data: Dict[str, Any],
    session_data: Dict[str, Any],
    task_name: str,
    username: str,
    rng=None,
) -> Optional[Dict[str, Any]]:
    rng = rng or random
    params: Dict[str, Any] = {'name': task_name, 'creator': username}
    groups = detect_template_entity_groups(template_data)
    entity_map = {
        'drone': session_data.get('drones', []) or [],
        'target': session_data.get('targets', []) or [],
        'obstacle': session_data.get('obstacles', []) or [],
    }

    for entity_type in ('drone', 'target', 'obstacle'):
        needed = [group for group in groups if group['entity_type'] == entity_type]
        available = entity_map[entity_type]
        if needed and not available:
            return None
        if not needed:
            continue
        if len(available) >= len(needed):
            selected_items = rng.sample(available, len(needed))
        else:
            selected_items = [rng.choice(available) for _ in range(len(needed))]
        for group, selected in zip(needed, selected_items):
            if group.get('id_param'):
                params[group['id_param']] = selected.get('id') or selected.get('name')
            if group.get('name_param'):
                params[group['name_param']] = selected.get('name') or selected.get('id')

    if entity_map['obstacle']:
        params['_context_obstacles'] = entity_map['obstacle']
    return params


def auto_create_tasks_for_session(
    *,
    api_server,
    template_manager,
    session_id: str,
    session_data: Dict[str, Any],
    session_name: str,
    session_task_type: str,
    task_count: int,
    username: str,
    logger=None,
    rng=None,
) -> AutoTaskGenerationResult:
    rng = rng or random
    existing_names = [task.get('name', '') for task in session_data.get('tasks', []) or []]
    suitable_templates = []
    for template_id, template_data in template_manager.get_all_templates().items():
        if template_data.get('exclude_in_random_generation', False):
            continue
        if template_matches_task_type(template_manager, template_data, session_task_type):
            suitable_templates.append((template_id, template_data))

    if not suitable_templates:
        if logger:
            logger.warning("No suitable templates found for auto task generation in session %s", session_id)
        return AutoTaskGenerationResult(task_count, 0, 0, 0, reason='no_suitable_templates')

    compatible_templates = []
    for template_id, template_data in suitable_templates:
        probe_name = create_new_name(template_data.get('name', 'Task'), exist_list=existing_names)
        if build_auto_template_params(template_data, session_data, probe_name, username, rng=rng):
            compatible_templates.append((template_id, template_data))

    if not compatible_templates:
        if logger:
            logger.warning(
                "No compatible templates found for auto task generation in session %s (%s)",
                session_id,
                session_name,
            )
        return AutoTaskGenerationResult(
            task_count,
            0,
            len(suitable_templates),
            0,
            reason='no_compatible_templates',
        )

    selected_indices = sorted(rng.randrange(len(compatible_templates)) for _ in range(task_count))

    created_count = 0
    for template_index in selected_indices:
        template_id, template_data = compatible_templates[template_index]
        base_name = template_data.get('name', 'Task')
        task_name = create_new_name(base_name, exist_list=existing_names)
        params = build_auto_template_params(template_data, session_data, task_name, username, rng=rng)
        if not params:
            continue
        task_data = template_manager.instantiate_template(template_id, params)
        if not task_data:
            continue
        result = api_server.api_create_task(session_id, task_data)
        if result:
            created_name = result.get('name', task_name)
            existing_names.append(created_name)
            session_data.setdefault('tasks', []).append({'name': created_name})
            created_count += 1

    if created_count < task_count and logger:
        logger.warning(
            "Created %s/%s auto-generated tasks for session %s",
            created_count,
            task_count,
            session_id,
        )

    reason = 'partial_failure' if created_count < task_count else None
    return AutoTaskGenerationResult(
        task_count,
        created_count,
        len(suitable_templates),
        len(compatible_templates),
        reason=reason,
    )
