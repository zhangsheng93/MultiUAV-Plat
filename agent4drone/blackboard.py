"""Local perception blackboard for UAV agent runs."""
from typing import Any, Optional


def _coordinate_tuple(value: Any) -> Any:
    if isinstance(value, dict) and "x" in value and "y" in value:
        point = (float(value["x"]), float(value["y"]))
        if "z" in value and value["z"] is not None:
            return (*point, float(value["z"]))
        return point
    if isinstance(value, (list, tuple)) and len(value) in {2, 3}:
        try:
            return tuple(float(component) for component in value)
        except (TypeError, ValueError):
            return value
    return value


def _vertices_tuples(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    return [_coordinate_tuple(vertex) for vertex in value]


class PerceptionBlackboard:
    """Per-command memory for locally sensed targets, obstacles, and drones."""

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id
        self.targets: dict[str, dict[str, Any]] = {}
        self.obstacles: dict[str, dict[str, Any]] = {}
        self.drones: dict[str, dict[str, Any]] = {}
        self._step = 0

    def clear(self) -> None:
        self.targets.clear()
        self.obstacles.clear()
        self.drones.clear()
        self._step = 0

    def next_step(self) -> int:
        self._step += 1
        return self._step

    def ingest_nearby(
        self,
        drone_id: str,
        nearby: dict[str, Any],
        observation_step: Optional[int] = None,
    ) -> dict[str, list[str]]:
        step = observation_step if observation_step is not None else self.next_step()
        changes = {
            "new_targets": [],
            "updated_targets": [],
            "new_obstacles": [],
            "updated_obstacles": [],
            "new_drones": [],
            "updated_drones": [],
        }
        self._ingest_entities(
            self.targets,
            changes,
            "target",
            "targets",
            nearby.get("targets", []),
            drone_id,
            step,
        )
        self._ingest_entities(
            self.obstacles,
            changes,
            "obstacle",
            "obstacles",
            nearby.get("obstacles", []),
            drone_id,
            step,
        )
        self._ingest_entities(
            self.drones,
            changes,
            "drone",
            "drones",
            nearby.get("drones", []),
            drone_id,
            step,
        )
        return changes

    def update_note(
        self,
        entity_kind: str,
        entity_id: str,
        note: str,
        priority: Optional[str] = None,
    ) -> dict[str, Any]:
        collection = self._collection_for_kind(entity_kind)
        entry = collection.get(entity_id)
        if not entry:
            raise KeyError(f"{entity_kind} {entity_id!r} is not in the perception blackboard")
        entry["note"] = str(note).strip()
        if priority is not None:
            normalized_priority = str(priority).strip().lower()
            if normalized_priority not in {"low", "medium", "high"}:
                raise ValueError("priority must be one of: low, medium, high")
            entry["priority"] = normalized_priority
        return entry

    def summary(self) -> dict[str, Any]:
        return {
            "targets": [self.compact_entry(entry) for entry in self.targets.values()],
            "obstacles": [self.compact_entry(entry) for entry in self.obstacles.values()],
            "drones": [self.compact_entry(entry) for entry in self.drones.values()],
        }

    def full(self) -> dict[str, Any]:
        return {
            "targets": list(self.targets.values()),
            "obstacles": list(self.obstacles.values()),
            "drones": list(self.drones.values()),
        }

    def compact_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        facts = entry.get("facts", {})
        compact = {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "category": entry.get("category"),
            "entity_type": entry.get("entity_type"),
            "position": facts.get("position"),
            "distance": facts.get("distance"),
            "note": entry.get("note"),
            "priority": entry.get("priority"),
        }
        for shape_key in ("radius", "vertices", "width", "height", "dimensions"):
            if shape_key in facts:
                compact[shape_key] = facts[shape_key]
        return {key: value for key, value in compact.items() if value is not None}

    def _collection_for_kind(self, entity_kind: str) -> dict[str, dict[str, Any]]:
        normalized = entity_kind.strip().lower()
        if normalized in {"target", "targets"}:
            return self.targets
        if normalized in {"obstacle", "obstacles"}:
            return self.obstacles
        if normalized in {"drone", "drones"}:
            return self.drones
        raise ValueError("entity_kind must be target, obstacle, or drone")

    def _ingest_entities(
        self,
        collection: dict[str, dict[str, Any]],
        changes: dict[str, list[str]],
        category: str,
        plural: str,
        entities: Any,
        observer_drone_id: str,
        step: int,
    ) -> None:
        if not isinstance(entities, list):
            return
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            entity_id = entity.get("id")
            if not entity_id:
                continue
            entity_id = str(entity_id)
            facts = self._facts_from_entity(entity)
            existing = collection.get(entity_id)
            if existing is None:
                collection[entity_id] = {
                    "id": entity_id,
                    "category": category,
                    "entity_type": entity.get("type"),
                    "name": entity.get("name"),
                    "facts": facts,
                    "note": None,
                    "priority": None,
                }
                changes[f"new_{plural}"].append(entity_id)
                continue

            existing["entity_type"] = entity.get("type", existing.get("entity_type"))
            existing["name"] = entity.get("name", existing.get("name"))
            existing["facts"] = facts
            changes[f"updated_{plural}"].append(entity_id)

    def _facts_from_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        facts = {}
        for key, value in entity.items():
            if key in {"id", "name"} or value is None:
                continue
            if key in {"position", "coordinates"}:
                facts[key] = _coordinate_tuple(value)
            elif key == "vertices":
                facts[key] = _vertices_tuples(value)
            else:
                facts[key] = value
        return facts
