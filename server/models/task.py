"""
MultiUAV-Plat Server System - Task Model

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

import time
import copy
from typing import Dict, List, Any, Optional, TypedDict
from enum import Enum

from config.util import generate_random_id


class TaskDifficulty(str, Enum):
    """Enum representing the difficulty level of a task"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RelatedAPI(TypedDict, total=False):
    """Type definition for a related API endpoint with parameters

    Attributes:
        endpoint: The API endpoint path (e.g., "/drones/{id}/command/move_to")
        parameters: Dictionary of parameter names to their descriptions or example values
    """
    endpoint: str
    parameters: Dict[str, Any]


class Task:
    """Model representing a task within a session that clients need to complete

    A Task represents a specific objective or activity that drones/clients should
    accomplish during a session. Tasks can include reconnaissance missions, area
    searches, target tracking, or any other mission objective.
    """

    def __init__(
        self,
        task_id: Optional[str] = None,
        name: str = "",
        content: str = "",
        content_aliases: Optional[List[str]] = None,
        description: str = "",
        creator: str = "unknown",
        originated_from: str = "unknown",
        difficulty: TaskDifficulty | str = TaskDifficulty.MEDIUM,
        related_apis: Optional[List[RelatedAPI]] = None,
        execution_check_apis: Optional[Dict[str, Any]] = None,
        commands: Optional[List[str]] = None,
        is_done: bool = False,
        is_passed: bool = False,
        created_at: Optional[float] = None,
        last_updated: Optional[float] = None
    ):
        """Initialize a Task

        Args:
            task_id: Optional specific ID for the task
            name: Short name/identifier for the task
            content: Detailed content/instructions for the task
            content_aliases: List of alternative names or aliases for the content
            description: Brief description of what the task entails
            creator: Who created this task (user role or username)
            originated_from: The principal (user/service) that created the task
            difficulty: Difficulty level of the task (easy, medium, or hard)
            related_apis: List of API endpoints used to execute the task
            execution_check_apis: Structured check definition (logic + checks) using /check endpoints
            commands: List of drone commands needed to complete this task
            is_done: Whether the task is completed
            is_passed: Whether the task has passed validation/checks
            created_at: Creation timestamp (defaults to current time)
            last_updated: Last update timestamp (defaults to current time)
        """
        self.id = task_id or generate_random_id()
        self.name = name
        self.content = content
        self.content_aliases = content_aliases or []
        self.description = description
        self.creator = creator
        self.originated_from = originated_from
        self.difficulty = self._coerce_difficulty(difficulty)
        self.related_apis = related_apis or []
        self.execution_check_apis = execution_check_apis or {}
        self.commands = commands or []
        self.is_done = is_done
        self.is_passed = is_passed

        now = time.time()
        self.created_at = created_at or now
        self.last_updated = last_updated or now

    @staticmethod
    def _coerce_difficulty(value: TaskDifficulty | str) -> TaskDifficulty:
        """Convert string or TaskDifficulty to TaskDifficulty enum"""
        if isinstance(value, TaskDifficulty):
            return value
        try:
            return TaskDifficulty(str(value))
        except ValueError:
            return TaskDifficulty.MEDIUM

    def mark_as_done(self) -> None:
        """Mark this task as completed"""
        self.is_done = True
        self.last_updated = time.time()

    def mark_as_pending(self) -> None:
        """Mark this task as pending (not completed)"""
        self.is_done = False
        self.last_updated = time.time()

    def update(self, updates: Dict[str, Any]) -> None:
        """Apply partial updates to the task

        Args:
            updates: Dictionary of field names to new values
        """
        changed = False

        if "name" in updates:
            self.name = updates["name"]
            changed = True

        if "content" in updates:
            self.content = updates["content"]
            changed = True

        if "content_aliases" in updates:
            self.content_aliases = updates["content_aliases"]
            changed = True

        if "description" in updates:
            self.description = updates["description"]
            changed = True

        if "creator" in updates:
            self.creator = updates["creator"]
            changed = True

        if "originated_from" in updates:
            self.originated_from = updates["originated_from"]
            changed = True

        if "difficulty" in updates:
            self.difficulty = self._coerce_difficulty(updates["difficulty"])
            changed = True

        if "related_apis" in updates:
            self.related_apis = updates["related_apis"]
            changed = True

        if "execution_check_apis" in updates:
            self.execution_check_apis = updates["execution_check_apis"]
            changed = True

        if "commands" in updates:
            self.commands = updates["commands"]
            changed = True

        if "is_done" in updates:
            self.is_done = bool(updates["is_done"])
            changed = True

        if "is_passed" in updates:
            self.is_passed = bool(updates["is_passed"])
            changed = True

        if changed:
            self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary representation

        Returns:
            Dictionary containing all task data
        """
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "content_aliases": self.content_aliases,
            "description": self.description,
            "creator": self.creator,
            "originated_from": self.originated_from,
            "difficulty": self.difficulty.value,
            "related_apis": [api.copy() for api in self.related_apis],
            "execution_check_apis": copy.deepcopy(self.execution_check_apis),
            "commands": self.commands.copy(),
            "is_done": self.is_done,
            "is_passed": self.is_passed,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task instance from a dictionary

        Args:
            data: Dictionary containing task data

        Returns:
            New Task instance

        Raises:
            ValueError: If required fields are missing
        """
        if "name" not in data:
            raise ValueError("Missing required field: name")

        return cls(
            name=data["name"],
            content=data.get("content", ""),
            content_aliases=data.get("content_aliases", []),
            description=data.get("description", ""),
            creator=data.get("creator", "unknown"),
            originated_from=data.get("originated_from", data.get("creator", "unknown")),
            difficulty=data.get("difficulty", TaskDifficulty.MEDIUM),
            related_apis=data.get("related_apis", []),
            execution_check_apis=data.get("execution_check_apis", {}),
            commands=data.get("commands", []),
            is_done=data.get("is_done", False),
            is_passed=data.get("is_passed", False),
            task_id=data.get("id"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated")
        )
