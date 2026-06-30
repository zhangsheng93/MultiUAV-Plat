import tempfile
import unittest

from task_auto_generator import auto_create_tasks_for_session
from task_template_manager import TaskTemplateManager


class FakeAPI:
    def __init__(self, fail_after=None):
        self.created_payloads = []
        self.fail_after = fail_after

    def api_create_task(self, session_id, payload):
        if self.fail_after is not None and len(self.created_payloads) >= self.fail_after:
            return None
        self.created_payloads.append(payload)
        return {"id": f"task-{len(self.created_payloads)}", "name": payload["name"]}


class FirstChoiceRandom:
    def randrange(self, stop):
        return 0

    def sample(self, population, k):
        return list(population[:k])

    def choice(self, population):
        return population[0]


class TestTaskAutoGenerator(unittest.TestCase):

    def build_manager(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        manager = TaskTemplateManager(template_dir=tmpdir.name)
        manager.builtin_templates = {}
        manager.templates = {}
        return manager

    def test_filters_templates_by_suitable_task(self):
        manager = self.build_manager()
        manager.add_template("tracking", {
            "name": "Tracking Task",
            "content": "Track {target_name}",
            "suitable_task": ["target_tracking"],
        })

        result = auto_create_tasks_for_session(
            api_server=FakeAPI(),
            template_manager=manager,
            session_id="session-1",
            session_data={"targets": [{"id": "t1", "name": "Target 1"}], "tasks": []},
            session_name="Session",
            session_task_type="area_search",
            task_count=1,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.reason, "no_suitable_templates")

    def test_excludes_templates_marked_out_of_random_generation(self):
        manager = self.build_manager()
        manager.add_template("excluded", {
            "name": "Excluded Task",
            "content": "Do not auto create",
            "suitable_task": ["all"],
            "exclude_in_random_generation": True,
        })
        manager.add_template("included", {
            "name": "Included Task",
            "content": "Auto create this",
            "suitable_task": ["all"],
        })
        api = FakeAPI()

        result = auto_create_tasks_for_session(
            api_server=api,
            template_manager=manager,
            session_id="session-1",
            session_data={"tasks": []},
            session_name="Session",
            session_task_type="others",
            task_count=1,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.suitable_template_count, 1)
        self.assertEqual(result.compatible_template_count, 1)
        self.assertEqual(api.created_payloads[0]["content"], "Auto create this")

    def test_returns_no_suitable_templates_when_all_matches_are_excluded(self):
        manager = self.build_manager()
        manager.add_template("excluded", {
            "name": "Excluded Task",
            "content": "Do not auto create",
            "suitable_task": ["all"],
            "exclude_in_random_generation": True,
        })

        result = auto_create_tasks_for_session(
            api_server=FakeAPI(),
            template_manager=manager,
            session_id="session-1",
            session_data={"tasks": []},
            session_name="Session",
            session_task_type="others",
            task_count=1,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.suitable_template_count, 0)
        self.assertEqual(result.compatible_template_count, 0)
        self.assertEqual(result.reason, "no_suitable_templates")

    def test_rejects_templates_when_required_entities_are_missing(self):
        manager = self.build_manager()
        manager.add_template("needs_drone", {
            "name": "Drone Task",
            "content": "Use {drone_name}",
            "suitable_task": ["all"],
        })

        result = auto_create_tasks_for_session(
            api_server=FakeAPI(),
            template_manager=manager,
            session_id="session-1",
            session_data={"drones": [], "tasks": []},
            session_name="Session",
            session_task_type="others",
            task_count=1,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 0)
        self.assertEqual(result.suitable_template_count, 1)
        self.assertEqual(result.compatible_template_count, 0)
        self.assertEqual(result.reason, "no_compatible_templates")

    def test_creates_unique_task_names_from_existing_tasks(self):
        manager = self.build_manager()
        manager.add_template("needs_drone", {
            "name": "Drone Task",
            "content": "Use {drone_name}",
            "suitable_task": ["all"],
        })
        api = FakeAPI()

        result = auto_create_tasks_for_session(
            api_server=api,
            template_manager=manager,
            session_id="session-1",
            session_data={
                "drones": [{"id": "d1", "name": "Drone 1"}],
                "tasks": [{"name": "Drone Task"}],
            },
            session_name="Session",
            session_task_type="others",
            task_count=2,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 2)
        self.assertEqual([payload["name"] for payload in api.created_payloads], ["Drone Task 1", "Drone Task 2"])
        self.assertEqual(api.created_payloads[0]["content"], "Use Drone 1")

    def test_returns_partial_success_when_api_creation_fails(self):
        manager = self.build_manager()
        manager.add_template("simple", {
            "name": "Simple Task",
            "content": "Do it",
            "suitable_task": ["all"],
        })

        result = auto_create_tasks_for_session(
            api_server=FakeAPI(fail_after=1),
            template_manager=manager,
            session_id="session-1",
            session_data={"tasks": []},
            session_name="Session",
            session_task_type="others",
            task_count=2,
            username="tester",
            rng=FirstChoiceRandom(),
        )

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.reason, "partial_failure")


if __name__ == "__main__":
    unittest.main()
