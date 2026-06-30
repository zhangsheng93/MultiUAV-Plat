import unittest
import logging
import math
from random_session_generator import RandomSessionGenerator, ITEM_SIZE_RANGES

class TestRandomSessionGenerator(unittest.TestCase):

    def setUp(self):
        # Suppress logging during tests
        logging.getLogger('random_session_generator').setLevel(logging.CRITICAL)
        self.generator = RandomSessionGenerator()

    def test_generate_session_data_counts(self):
        drone_count = 5
        target_count = 3
        obstacle_count = 2
        
        data = self.generator.generate_session_data(
            drone_count=drone_count,
            target_count=target_count,
            obstacle_count=obstacle_count,
            area_width=1000,
            area_height=1000
        )
        
        self.assertEqual(len(data['drones']), drone_count)
        self.assertEqual(len(data['targets']), target_count)
        self.assertEqual(len(data['obstacles']), obstacle_count)

    def test_generate_session_data_structure(self):
        data = self.generator.generate_session_data(1, 1, 1)
        
        # Check drone
        drone = data['drones'][0]
        self.assertIn('name', drone)
        self.assertIn('model', drone)
        self.assertIn('position', drone)
        self.assertIn('x', drone['position'])
        self.assertIn('y', drone['position'])
        self.assertIn('z', drone['position'])
        
        # Check target
        target = data['targets'][0]
        self.assertIn('name', target)
        self.assertIn('type', target)
        self.assertIn('position', target)
        self.assertTrue('radius' in target or 'vertices' in target)
        
        # Check obstacle
        obstacle = data['obstacles'][0]
        self.assertIn('name', obstacle)
        self.assertIn('type', obstacle)
        self.assertIn('position', obstacle)

    def test_generate_environment_payload(self):
        payload = self.generator.generate_environment_payload("Test Session")
        self.assertIn("Test Session", payload['name'])
        self.assertIn('weather', payload)
        self.assertIn('temperature', payload)

    def test_generate_session_description(self):
        desc = self.generator.generate_session_description(
            name="Session 1",
            area_width=1000,
            area_height=1000,
            task_type="area_search",
            populate_random=True,
            drone_count=2,
            target_count=2,
            obstacle_count=2,
            with_examples=False
        )
        self.assertIn("Session 1", desc)
        self.assertIn("1000×1000 m", desc)
        self.assertIn("area search", desc)
        self.assertIn("2 drones", desc)

    def test_generate_session_data_default_drone_positions_within_full_map(self):
        area_width = 1000
        area_height = 800

        data = self.generator.generate_session_data(
            drone_count=6,
            target_count=0,
            obstacle_count=0,
            area_width=area_width,
            area_height=area_height,
            do_not_scatter_drones=False
        )

        for drone in data['drones']:
            position = drone['position']
            self.assertGreaterEqual(position['x'], 0)
            self.assertLessEqual(position['x'], area_width)
            self.assertGreaterEqual(position['y'], 0)
            self.assertLessEqual(position['y'], area_height)

    def test_generate_session_data_clusters_drones_near_origin_when_enabled(self):
        drone_count = 7
        area_width = 1000
        area_height = 800
        buffer_radius = float(ITEM_SIZE_RANGES['drone']['buffer'])

        data = self.generator.generate_session_data(
            drone_count=drone_count,
            target_count=0,
            obstacle_count=0,
            area_width=area_width,
            area_height=area_height,
            do_not_scatter_drones=True
        )

        x_range, y_range = self.generator._drone_placement_ranges(
            area_width=area_width,
            area_height=area_height,
            drone_count=drone_count,
            do_not_scatter_drones=True
        )

        drone_positions = []
        for drone in data['drones']:
            position = drone['position']
            self.assertGreaterEqual(position['x'], x_range[0])
            self.assertLessEqual(position['x'], x_range[1])
            self.assertGreaterEqual(position['y'], y_range[0])
            self.assertLessEqual(position['y'], y_range[1])
            drone_positions.append((position['x'], position['y']))

        for index, (x1, y1) in enumerate(drone_positions):
            for x2, y2 in drone_positions[index + 1:]:
                distance = math.dist((x1, y1), (x2, y2))
                self.assertGreaterEqual(distance, buffer_radius * 2.0 - 2.0)

    def test_generate_session_data_generates_drones_first_when_not_scattering(self):
        class RecordingGenerator(RandomSessionGenerator):
            def __init__(self):
                super().__init__()
                self.call_order = []

            def _random_drone_payload(self, *args, **kwargs):
                self.call_order.append('drone')
                return super()._random_drone_payload(*args, **kwargs)

            def _random_target_payload(self, *args, **kwargs):
                self.call_order.append('target')
                return super()._random_target_payload(*args, **kwargs)

            def _random_obstacle_payload(self, *args, **kwargs):
                self.call_order.append('obstacle')
                return super()._random_obstacle_payload(*args, **kwargs)

        generator = RecordingGenerator()
        generator.generate_session_data(
            drone_count=2,
            target_count=1,
            obstacle_count=1,
            area_width=1000,
            area_height=800,
            do_not_scatter_drones=True
        )

        self.assertEqual(generator.call_order[:2], ['drone', 'drone'])

if __name__ == '__main__':
    unittest.main()
