from typing import Any, Dict, Optional


def extract_original_task_command(task: Optional[Dict[str, Any]]) -> str:
    """Return a task's original command content, stripped of surrounding whitespace."""
    if not isinstance(task, dict):
        return ""
    content = task.get("content", "")
    if content is None:
        return ""
    return str(content).strip()
