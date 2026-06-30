import json
import tempfile
import unittest
from pathlib import Path

from task_template_dialog import format_suitable_task_label, template_matches_task_type
from task_template_manager import TaskTemplateManager

NEW_TARGET_ASSIGNMENT_TEMPLATE_IDS = [
    "dual_drone_same_target",
    "triple_drone_target_search",
    "relay_find_and_support_target",
    "cross_target_swap_after_discovery",
    "two_find_two_support",
]


class TestTaskTemplateManagerSuitableTask(unittest.TestCase):

    def test_normalize_suitable_task_values(self):
        self.assertEqual(TaskTemplateManager.normalize_suitable_task(None), [])
        self.assertEqual(TaskTemplateManager.normalize_suitable_task(""), [])
        self.assertEqual(
            TaskTemplateManager.normalize_suitable_task([
                "area_search",
                "invalid",
                "area_search",
                "target_tracking",
                123,
            ]),
            ["area_search", "target_tracking"],
        )
        self.assertEqual(
            TaskTemplateManager.normalize_suitable_task("target_assignment"),
            ["target_assignment"],
        )

    def test_load_templates_normalizes_legacy_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "task_templates.json"
            templates_path.write_text(json.dumps({
                "legacy_all": {
                    "name": "Legacy All",
                },
                "legacy_scalar": {
                    "name": "Legacy Scalar",
                    "suitable_task": "area_search",
                },
                "legacy_mixed": {
                    "name": "Legacy Mixed",
                    "suitable_task": ["target_tracking", "invalid", "target_tracking"],
                },
            }), encoding="utf-8")

            manager = TaskTemplateManager(template_dir=tmpdir)

            self.assertEqual(manager.get_template("legacy_all")["suitable_task"], [])
            self.assertFalse(manager.get_template("legacy_all")["exclude_in_random_generation"])
            self.assertEqual(
                manager.get_template("legacy_scalar")["suitable_task"],
                ["area_search"],
            )
            self.assertEqual(
                manager.get_template("legacy_mixed")["suitable_task"],
                ["target_tracking"],
            )

    def test_save_and_reload_preserves_exclude_in_random_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            success = manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Do something",
                "exclude_in_random_generation": True,
            })
            self.assertTrue(success)

            reloaded = TaskTemplateManager(template_dir=tmpdir)
            self.assertTrue(
                reloaded.get_template("custom_template")["exclude_in_random_generation"]
            )
            metadata = reloaded.get_template_list()
            custom_metadata = next(
                template for template in metadata
                if template["id"] == "custom_template"
            )
            self.assertTrue(custom_metadata["exclude_in_random_generation"])

    def test_template_list_reports_execution_check_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            success = manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Do something",
                "related_apis": [
                    {"endpoint": "/api/one"},
                    {"endpoint": "/api/two"},
                ],
                "execution_check_apis": {
                    "logic": "and",
                    "checks": [
                        {"endpoint": "/check/one"},
                        {
                            "logic": "or",
                            "checks": [
                                {"endpoint": "/check/two"},
                                {"endpoint": "/check/three"},
                            ],
                        },
                    ],
                },
            })
            self.assertTrue(success)

            metadata = manager.get_template_list()
            custom_metadata = next(
                template for template in metadata
                if template["id"] == "custom_template"
            )
            self.assertEqual(custom_metadata["api_count"], 2)
            self.assertEqual(custom_metadata["check_count"], 3)

    def test_save_and_reload_preserves_normalized_suitable_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            success = manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Do something",
                "suitable_task": ["others", "invalid", "others", "area_search"],
            })
            self.assertTrue(success)

            reloaded = TaskTemplateManager(template_dir=tmpdir)
            self.assertEqual(
                reloaded.get_template("custom_template")["suitable_task"],
                ["others", "area_search"],
            )

    def test_instantiate_template_does_not_copy_suitable_task(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Do something",
                "suitable_task": ["target_assignment"],
                "exclude_in_random_generation": True,
            })

            instantiated = manager.instantiate_template("custom_template")
            self.assertNotIn("suitable_task", instantiated)
            self.assertNotIn("exclude_in_random_generation", instantiated)

    def test_instantiate_template_collapses_duplicate_drone_prefix_in_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Drone {drone_name} must take off",
            })

            instantiated = manager.instantiate_template("custom_template", {
                "drone_name": "Drone X",
            })

            self.assertEqual(instantiated["content"], "Drone X must take off")

    def test_instantiate_template_collapses_duplicate_drone_prefix_in_content_aliases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "Use {drone_name}",
                "content_aliases": [
                    "drone {drone_name} take photo",
                    "Drone {drone_name} inspect target",
                ],
            })

            instantiated = manager.instantiate_template("custom_template", {
                "drone_name": "Drone X",
            })

            self.assertEqual(instantiated["content_aliases"][0], "drone X take photo")
            self.assertEqual(instantiated["content_aliases"][1], "Drone X inspect target")

    def test_instantiate_template_keeps_standalone_drone_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(template_dir=tmpdir)
            manager.add_template("custom_template", {
                "name": "Custom Template",
                "content": "{drone_name} must take off",
            })

            instantiated = manager.instantiate_template("custom_template", {
                "drone_name": "Drone X",
            })

            self.assertEqual(instantiated["content"], "Drone X must take off")

    def test_filter_helpers(self):
        all_template = {"suitable_task": ["all"]}
        tracking_template = {"suitable_task": ["target_tracking"]}

        self.assertTrue(template_matches_task_type(all_template, "area_search"))
        self.assertTrue(template_matches_task_type(tracking_template, "target_tracking"))
        self.assertFalse(template_matches_task_type(tracking_template, "area_search"))
        self.assertEqual(format_suitable_task_label(["all"]), "All")
        self.assertEqual(format_suitable_task_label([]), "All")
        self.assertEqual(
            format_suitable_task_label(["target_tracking", "area_search"]),
            "Target Tracking, Area Search",
        )

    def test_builtin_templates_are_backfilled_with_suitable_task(self):
        manager = TaskTemplateManager()
        self.assertEqual(
            manager.get_template("search_task_with_photo")["suitable_task"],
            ["all"],
        )
        self.assertEqual(
            manager.get_template("adaptive_search_and_track")["suitable_task"],
            ["target_tracking"],
        )
        self.assertEqual(
            manager.get_template("target_assignment")["suitable_task"],
            ["target_assignment"],
        )
        self.assertEqual(
            manager.get_template("basic_takeoff")["suitable_task"],
            ["all"],
        )

    def test_new_builtin_target_assignment_templates_load_with_expected_metadata(self):
        manager = TaskTemplateManager()

        for template_id in NEW_TARGET_ASSIGNMENT_TEMPLATE_IDS:
            with self.subTest(template_id=template_id):
                template = manager.get_template(template_id)
                self.assertIsNotNone(template)
                self.assertTrue(template["is_builtin"])
                self.assertEqual(template["suitable_task"], ["target_assignment"])

    def test_new_builtin_target_assignment_templates_do_not_leak_suitable_task_on_instantiation(self):
        manager = TaskTemplateManager()

        template_parameters = {
            "dual_drone_same_target": {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "target_id": "target-red",
                "target_name": "Red Target",
            },
            "triple_drone_target_search": {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "drone_3_id": "drone-charlie",
                "drone_3_name": "Charlie",
                "target_id": "target-red",
                "target_name": "Red Target",
            },
            "relay_find_and_support_target": {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "target_id": "target-red",
                "target_name": "Red Target",
            },
            "cross_target_swap_after_discovery": {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "target_1_id": "target-red",
                "target_1_name": "Red Target",
                "target_2_id": "target-blue",
                "target_2_name": "Blue Target",
            },
            "two_find_two_support": {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "drone_3_id": "drone-charlie",
                "drone_3_name": "Charlie",
                "drone_4_id": "drone-delta",
                "drone_4_name": "Delta",
                "target_1_id": "target-red",
                "target_1_name": "Red Target",
                "target_2_id": "target-blue",
                "target_2_name": "Blue Target",
            },
        }

        for template_id, parameters in template_parameters.items():
            with self.subTest(template_id=template_id):
                instantiated = manager.instantiate_template(template_id, parameters)
                self.assertNotIn("suitable_task", instantiated)

    def test_dual_patrol_substitutes_waypoints_and_checks_all_route_points(self):
        manager = TaskTemplateManager()
        instantiated = manager.instantiate_template(
            "dual_patrol",
            {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
            },
        )

        def assert_no_placeholders(value):
            if isinstance(value, dict):
                for child_value in value.values():
                    assert_no_placeholders(child_value)
            elif isinstance(value, list):
                for child_value in value:
                    assert_no_placeholders(child_value)
            elif isinstance(value, str):
                self.assertNotRegex(value, r"\{[^{}]+\}")

        assert_no_placeholders([
            api["parameters"] for api in instantiated["related_apis"]
        ])
        assert_no_placeholders(instantiated["execution_check_apis"])

        drone_1_path = instantiated["related_apis"][2]["parameters"]["waypoints"]
        drone_2_path = instantiated["related_apis"][3]["parameters"]["waypoints"]
        checks = instantiated["execution_check_apis"]["checks"]

        self.assertEqual(len(checks), 4)
        for waypoint in [*drone_1_path, *drone_2_path]:
            for coordinate in ("x", "y", "z"):
                self.assertIsInstance(waypoint[coordinate], float)

        expected_checks = [
            ("drone-alpha", drone_1_path[0]),
            ("drone-alpha", drone_1_path[1]),
            ("drone-bravo", drone_2_path[0]),
            ("drone-bravo", drone_2_path[1]),
        ]
        for check, (expected_drone_id, expected_waypoint) in zip(checks, expected_checks):
            params = check["parameters"]
            self.assertEqual(params["drone_id"], expected_drone_id)
            self.assertEqual(params["x"], expected_waypoint["x"])
            self.assertEqual(params["y"], expected_waypoint["y"])
            self.assertEqual(params["z"], expected_waypoint["z"])
            self.assertEqual(params["tolerance"], 3.0)

    def test_representative_new_template_instantiation_replaces_indexed_placeholders(self):
        manager = TaskTemplateManager()
        instantiated = manager.instantiate_template(
            "two_find_two_support",
            {
                "drone_1_id": "drone-alpha",
                "drone_1_name": "Alpha",
                "drone_2_id": "drone-bravo",
                "drone_2_name": "Bravo",
                "drone_3_id": "drone-charlie",
                "drone_3_name": "Charlie",
                "drone_4_id": "drone-delta",
                "drone_4_name": "Delta",
                "target_1_id": "target-red",
                "target_1_name": "Red Target",
                "target_2_id": "target-blue",
                "target_2_name": "Blue Target",
            },
        )

        self.assertIn("Alpha", instantiated["content"])
        self.assertIn("Delta", instantiated["content"])
        self.assertIn("Red Target", instantiated["content"])
        self.assertIn("Blue Target", instantiated["content"])
        self.assertEqual(instantiated["related_apis"][0]["parameters"]["id"], "drone-alpha")
        self.assertEqual(instantiated["related_apis"][3]["parameters"]["id"], "drone-delta")
        self.assertEqual(
            instantiated["execution_check_apis"]["checks"][0]["parameters"]["target_id"],
            "target-red",
        )
        self.assertEqual(
            instantiated["execution_check_apis"]["checks"][3]["parameters"]["target_id"],
            "target-blue",
        )


if __name__ == "__main__":
    unittest.main()
