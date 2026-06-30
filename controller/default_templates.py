#!/usr/bin/env python3
"""
Default Templates for AI Agent Testing

These templates have enhanced content fields that clearly specify:
1. Which drone to use (with placeholder)
2. Exact positions/altitudes
3. All required parameters
4. Multiple content_aliases for testing different phrasings

The content and content_aliases serve as ground truth instructions for AI agents,
while related_apis serve as the expected API calls for validation.
"""

DEFAULT_TEMPLATES = {
    # ===== Basic Operations =====
        'basic_takeoff': {
            'name': 'Basic Takeoff',
            'description': 'Simple takeoff to altitude and hover - AI Testing Template',
            'content': 'Command drone {drone_name} to take off to an altitude of {random_takeoffalt:8:15} meters and hover in place.',
            'content_aliases': [
                'make drone {drone_name} takeoff to {random_takeoffalt:8:15} meters and hover',
                'fly drone {drone_name} up to {random_takeoffalt:8:15}m and hold position',
                'drone {drone_name} take off {random_takeoffalt:8:15} meters and remain airborne',
                'basic flight: drone {drone_name} goes up to {random_takeoffalt:8:15}m and hovers',
                '{drone_name} takeoff {random_takeoffalt:8:15}m hover'
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_takeoffalt:8:15}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_altitude',
                        'parameters': {'drone_id': '{drone_id}', 'expected_altitude': '{random_takeoffalt:8:15}', 'tolerance': 2.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 1.5},
                        'expect': False
                    }
                ]
            },
            'commands': ['take_off', 'hover']
        },

        'complete_flight_cycle': {
            'name': 'Complete Flight Cycle Verification',
            'description': 'Full takeoff, mission, and landing cycle - uses history checks',
            'content': 'Drone {drone_name} complete flight cycle test: verify full operational capability by taking off to {randz_cycle:15:20} meters (must achieve takeoff), fly to waypoint ({randx_cycle:350:600}, {randy_cycle:350:600}, {randz_cycle}), hover briefly, then return home and land properly. This validates complete flight cycle.',
            'content_aliases': [
                'Execute full operational test for drone {drone_name}: lift off to {randz_cycle:15:20} meters altitude, navigate to position ({randx_cycle:350:600}, {randy_cycle:350:600}, {randz_cycle}), pause in hover, then return to home base and perform landing.',
                'Drone {drone_name} complete mission sequence: ascend to {randz_cycle:15:20}m, proceed to waypoint coordinates ({randx_cycle:350:600}, {randy_cycle:350:600}, {randz_cycle}), hover momentarily, fly back home and land safely.',
                'Run end-to-end flight verification on {drone_name}: take off reaching {randz_cycle:15:20} meters, fly to target location ({randx_cycle:350:600}, {randy_cycle:350:600}, {randz_cycle}), hold position briefly, return home and complete landing procedure.',
                'Full cycle test {drone_name}: departure to altitude {randz_cycle:15:20}m, travel to ({randx_cycle:350:600}, {randy_cycle:350:600}, {randz_cycle}), hover in place, come back home and land properly to validate complete flight capability.',
                'Command {drone_name} complete flight validation: achieve takeoff at {randz_cycle:15:20} meters height, move to position x={randx_cycle:350:600} y={randy_cycle:350:600} z={randz_cycle}, maintain hover, then execute return home and landing to verify full operational cycle.',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_cycle}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_cycle}', 'y': '{randy_cycle}', 'z': '{randz_cycle}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/return_home', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_id}', 'min_altitude': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_cycle}', 'y': '{randy_cycle}', 'z': '{randz_cycle}', 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_landed',
                        'parameters': {'drone_id': '{drone_id}', 'max_altitude': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_at_home',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover', 'return_home', 'land']
        },

        'set_new_home': {
            'name': 'Set New Home Position',
            'description': 'Take off, fly to a new position, and set it as home on the ground',
            'content': 'Drone {drone_name} takes off to {randz_flight:10:15} meters, flies to position ({randx_home:150:400}, {randy_home:150:400}, {randz_flight:10:15}), descends and lands at ground level, sets this ground position as the new home.',
            'content_aliases': [
                '{drone_name} take off to {randz_flight:10:15}m, fly to ({randx_home:150:400},{randy_home:150:400},{randz_flight:10:15}), land there, and set that ground spot as home',
                'make drone {drone_name} climb to {randz_flight:10:15} meters, move to coordinates {randx_home:150:400} {randy_home:150:400} at {randz_flight:10:15}m, land, then set home on ground',
                '{drone_name} home relocation mission: fly at {randz_flight:10:15}m to ground base coordinates {randx_home:150:400} {randy_home:150:400}, descend, land, and save the new home',
                'drone {drone_name} establish new base by taking off to {randz_flight:10:15}m, reaching ({randx_home:150:400}, {randy_home:150:400}, {randz_flight:10:15}), landing, and setting home',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': True,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_flight:10:15}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_home:150:400}', 'y': '{randy_home:150:400}', 'z': '{randz_flight:10:15}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/set_home', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_at_home',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 2.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'land', 'set_home']
        },

        'simple_altitude_change': {
            'name': 'Simple Altitude Change',
            'description': 'Take off and change altitude to a specific height',
            'content': 'Drone {drone_name} should take off to {random_initialalt:10:15} meters, then climb to {random_finalalt:20:30} meters altitude and hover.',
            'content_aliases': [
                '{drone_name} takeoff {random_initialalt:10:15}m then climb to {random_finalalt:20:30}m',
                'make drone {drone_name} go up to {random_initialalt:10:15} meters then higher to {random_finalalt:20:30}',
                '{drone_name} altitude test: start {random_initialalt:10:15}m, end {random_finalalt:20:30}m',
                'drone {drone_name} two-step climb: first take off to {random_initialalt:10:15} meters, then change altitude to {random_finalalt:20:30} meters',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_initialalt:10:15}'}},
                {'endpoint': '/drones/{id}/command/change_altitude', 'parameters': {'id': '{drone_id}', 'altitude': '{random_finalalt:20:30}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_altitude',
                        'parameters': {'drone_id': '{drone_id}', 'expected_altitude': '{random_finalalt:20:30}', 'tolerance': 2.0}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['take_off', 'change_altitude', 'hover']
        },

        'simple_rotation': {
            'name': 'Simple Rotation Test',
            'description': 'Take off and rotate to face a specific direction',
            'content': 'Drone {drone_name} takes off to {random_rotalt:10:15} meters altitude, then rotates to face heading {randint_heading:0:360} degrees and hovers.',
            'content_aliases': [
                '{drone_name} takeoff {random_rotalt:10:15}m and turn to {randint_heading:0:360} degrees',
                'make drone {drone_name} fly up to {random_rotalt:10:15} meters then face direction {randint_heading:0:360}',
                '{drone_name} orientation test: altitude {random_rotalt:10:15}m heading {randint_heading:0:360}',
                'drone {drone_name} airborne rotation to {randint_heading:0:360} degrees at {random_rotalt:10:15}m',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_rotalt:10:15}'}},
                {'endpoint': '/drones/{id}/command/rotate', 'parameters': {'id': '{drone_id}', 'heading': '{randint_heading:0:360}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_heading',
                        'parameters': {'drone_id': '{drone_id}', 'expected_heading': '{randint_heading:0:360}', 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_altitude',
                        'parameters': {'drone_id': '{drone_id}', 'expected_altitude': '{random_rotalt:10:15}', 'tolerance': 2.0}
                    }
                ]
            },
            'commands': ['take_off', 'rotate', 'hover']
        },


        'takeoff_and_photo': {
            'name': 'Randomized Loiter with Photo',
            'description': 'Demonstrates sticky vs per-occurrence random placeholders',
            'content': 
                "Drone {drone_name} takes off to {randz_loiter} meters, flies to ({randx_loiter}, {randy_loiter}, {randz_loiter}), loiters for {randint_sec:5:12} seconds, and captures a photo.",
            'content_aliases': [
                'Launch {drone_name} to random coordinates {randx_loiter},{randy_loiter} at {randz_loiter}m altitude, pause {randint_sec:5:12}s, take photograph',
                '{drone_name} performs randomized observation flight: ascend {randz_loiter}m, navigate to ({randx_loiter},{randy_loiter},{randz_loiter}), loiter {randint_sec:5:12} seconds, capture image',
                'Random reconnaissance point for {drone_name}: fly to altitude {randz_loiter}m, reach position ({randx_loiter},{randy_loiter}), wait {randint_sec:5:12}s, then photograph',
                'Send {drone_name} on variable scouting mission to ({randx_loiter},{randy_loiter},{randz_loiter}) with {randint_sec:5:12}s hover time, and take a photo',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_loiter}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_loiter}', 'y': '{randy_loiter}', 'z': '{randz_loiter}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}', 'duration': '{randint_sec:5:12}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_loiter}', 'y': '{randy_loiter}', 'z': '{randz_loiter}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 1}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover', 'take_photo']
        },

        'emergency_return': {
            'name': 'Emergency Return to Home',
            'description': 'Immediate RTH and landing',
            'content': 'Drone {drone_name} must immediately execute return to home procedure and land. This is an emergency abort mission command.',
            'content_aliases': [
                '{drone_name} emergency return home now',
                'abort mission for drone {drone_name} and return to base',
                'RTH for {drone_name} immediate landing',
                'drone {drone_name} come back home and land immediately',
                'emergency: {drone_name} return and land',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Basic Operations',
            'is_builtin': True,
            'exclude_in_random_generation': True,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/return_home', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_at_home',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['return_home', 'land']
        },

    # ===== Navigation =====
        'quick_checkpoint': {
            'name': 'Quick Checkpoint Visit',
            'description': 'Fly to a single checkpoint',
            'content': 'Drone {drone_name} takes off to {randz_check:12:18} meters, flies to checkpoint at ({randx_check:350:600}, {randy_check:350:600}, {randz_check:12:18}), and hovers briefly.',
            'content_aliases': [
                'Send {drone_name} to verify checkpoint location: lift off to {randz_check:12:18} meters, fly to position ({randx_check:350:600}, {randy_check:350:600}, {randz_check:12:18}), then hover briefly.',
                'Command drone {drone_name} to ascend to {randz_check:12:18}m altitude, navigate to waypoint coordinates ({randx_check:350:600}, {randy_check:350:600}, {randz_check:12:18}), and maintain hover.',
                '{drone_name} checkpoint verification flight: take off reaching {randz_check:12:18} meters height, proceed to position x={randx_check:350:600} y={randy_check:350:600} z={randz_check:12:18}, pause in place.',
                'Execute quick point-to-point mission for {drone_name}: departure to {randz_check:12:18}m elevation, travel to checkpoint ({randx_check:350:600}, {randy_check:350:600}, {randz_check:12:18}), hold position briefly.',
                'Drone {drone_name} single waypoint visit: take off to altitude {randz_check:12:18} meters, move to target location ({randx_check:350:600}, {randy_check:350:600}, {randz_check:12:18}), then hover momentarily.',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_check:12:18}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_check:350:600}', 'y': '{randy_check:350:600}', 'z': '{randz_check:12:18}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_check:350:600}', 'y': '{randy_check:350:600}', 'z': '{randz_check:12:18}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover']
        },

        'fly_several_waypoints': {
            'name': 'Fly Several Waypoints',
            'description': 'Visit multiple waypoints to test multi-position navigation',
            'content': 'Drone {drone_name} should take off to {randz_wpalt:15:22} meters and fly through multiple waypoints: ({randx_wp1:100:300}, {randy_wp1:100:250}, {randz_wpalt:15:22}), ({randx_wp2:400:600}, {randy_wp2:100:250}, {randz_wpalt:15:22}), ({randx_wp3:700:900}, {randy_wp3:250:500}, {randz_wpalt:15:22}), ({randx_wp4:400:600}, {randy_wp4:500:650}, {randz_wpalt:15:22}), ({randx_wp5:100:300}, {randy_wp5:500:650}, {randz_wpalt:15:22}).',
            'content_aliases': [
                'Command {drone_name} to navigate a route of 5 waypoints at {randz_wpalt:15:22}m altitude: ({randx_wp1:100:300},{randy_wp1:100:250}), ({randx_wp2:400:600},{randy_wp2:100:250}), ({randx_wp3:700:900},{randy_wp3:250:500}), ({randx_wp4:400:600},{randy_wp4:500:650}), ({randx_wp5:100:300},{randy_wp5:500:650}).',
                '{drone_name} multi-stop flight plan: ascend to {randz_wpalt:15:22} meters, then proceed through coordinates ({randx_wp1:100:300},{randy_wp1:100:250}), ({randx_wp2:400:600},{randy_wp2:100:250}), ({randx_wp3:700:900},{randy_wp3:250:500}), ({randx_wp4:400:600},{randy_wp4:500:650}), ({randx_wp5:100:300},{randy_wp5:500:650}).',
                'Task {drone_name} with sequential navigation: visit 5 locations at {randz_wpalt:15:22}m, specifically ({randx_wp1:100:300},{randy_wp1:100:250}), ({randx_wp2:400:600},{randy_wp2:100:250}), ({randx_wp3:700:900},{randy_wp3:250:500}), ({randx_wp4:400:600},{randy_wp4:500:650}), ({randx_wp5:100:300},{randy_wp5:500:650}).',
                '{drone_name} advanced waypoint mission: takeoff {randz_wpalt:15:22}m, then fly to the five points specified: WP1({randx_wp1:100:300},{randy_wp1:100:250}), WP2({randx_wp2:400:600},{randy_wp2:100:250}), WP3({randx_wp3:700:900},{randy_wp3:250:500}), WP4({randx_wp4:400:600},{randy_wp4:500:650}), WP5({randx_wp5:100:300},{randy_wp5:500:650}).',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_wpalt:15:22}'}},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_id}',
                    'waypoints': [
                        {'x': '{randx_wp1:100:300}', 'y': '{randy_wp1:100:250}', 'z': '{randz_wpalt:15:22}'},
                        {'x': '{randx_wp2:400:600}', 'y': '{randy_wp2:100:250}', 'z': '{randz_wpalt:15:22}'},
                        {'x': '{randx_wp3:700:900}', 'y': '{randy_wp3:250:500}', 'z': '{randz_wpalt:15:22}'},
                        {'x': '{randx_wp4:400:600}', 'y': '{randy_wp4:500:650}', 'z': '{randz_wpalt:15:22}'},
                        {'x': '{randx_wp5:100:300}', 'y': '{randy_wp5:500:650}', 'z': '{randz_wpalt:15:22}'}
                    ]
                }}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp1:100:300}', 'y': '{randy_wp1:100:250}', 'z': '{randz_wpalt:15:22}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp2:400:600}', 'y': '{randy_wp2:100:250}', 'z': '{randz_wpalt:15:22}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp3:700:900}', 'y': '{randy_wp3:250:500}', 'z': '{randz_wpalt:15:22}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp4:400:600}', 'y': '{randy_wp4:500:650}', 'z': '{randz_wpalt:15:22}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp5:100:300}', 'y': '{randy_wp5:500:650}', 'z': '{randz_wpalt:15:22}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_along_path']
        },

        'patrol_mission': {
            'name': 'Patrol Mission - Quadrangle',
            'description': 'Patrol a random quadrangle path covering four map quadrants',
            'content': (
                "Drone {drone_name} should take off to {randz_patrolalt:12:18} meters altitude, then fly a quadrangle patrol "
                "route visiting four points in different sectors: ({randx_q1:100:400}, {randy_q1:100:400}, {randz_patrolalt:12:18}), "
                "({randx_q2:600:900}, {randy_q2:100:400}, {randz_patrolalt:12:18}), "
                "({randx_q3:600:900}, {randy_q3:600:900}, {randz_patrolalt:12:18}), "
                "({randx_q4:100:400}, {randy_q4:600:900}, {randz_patrolalt:12:18}), "
                "and finally return to the start point ({randx_q1:100:400}, {randy_q1:100:400}, {randz_patrolalt:12:18})."
            ),
            'content_aliases': [
                'make {drone_name} patrol quadrangle path: {randx_q1:100:400},{randy_q1:100:400} -> {randx_q2:600:900},{randy_q2:100:400} -> {randx_q3:600:900},{randy_q3:600:900} -> {randx_q4:100:400},{randy_q4:600:900} -> start at {randz_patrolalt:12:18}m',
                'drone {drone_name} fly loop at {randz_patrolalt:12:18}m through four sectors: SW ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18}), SE ({randx_q2:600:900},{randy_q2:100:400},{randz_patrolalt:12:18}), NE ({randx_q3:600:900},{randy_q3:600:900},{randz_patrolalt:12:18}), NW ({randx_q4:100:400},{randy_q4:600:900},{randz_patrolalt:12:18}), then back to ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18})',
                '{drone_name} takeoff {randz_patrolalt:12:18}m and patrol 4 random points covering the map: ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18}), ({randx_q2:600:900},{randy_q2:100:400},{randz_patrolalt:12:18}), ({randx_q3:600:900},{randy_q3:600:900},{randz_patrolalt:12:18}), ({randx_q4:100:400},{randy_q4:600:900},{randz_patrolalt:12:18}), return to ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18})',
                'fly {drone_name} in a quadrangle pattern at {randz_patrolalt:12:18} meters, visiting ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18}) -> ({randx_q2:600:900},{randy_q2:100:400},{randz_patrolalt:12:18}) -> ({randx_q3:600:900},{randy_q3:600:900},{randz_patrolalt:12:18}) -> ({randx_q4:100:400},{randy_q4:600:900},{randz_patrolalt:12:18}) -> ({randx_q1:100:400},{randy_q1:100:400},{randz_patrolalt:12:18})',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_patrolalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_id}',
                    'waypoints': [
                        {'x': '{randx_q1:100:400}', 'y': '{randy_q1:100:400}', 'z': '{randz_patrolalt:12:18}'},
                        {'x': '{randx_q2:600:900}', 'y': '{randy_q2:100:400}', 'z': '{randz_patrolalt:12:18}'},
                        {'x': '{randx_q3:600:900}', 'y': '{randy_q3:600:900}', 'z': '{randz_patrolalt:12:18}'},
                        {'x': '{randx_q4:100:400}', 'y': '{randy_q4:600:900}', 'z': '{randz_patrolalt:12:18}'},
                        {'x': '{randx_q1:100:400}', 'y': '{randy_q1:100:400}', 'z': '{randz_patrolalt:12:18}'}
                    ]
                }}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_q1:100:400}', 'y': '{randy_q1:100:400}', 'z': '{randz_patrolalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_q2:600:900}', 'y': '{randy_q2:100:400}', 'z': '{randz_patrolalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_q3:600:900}', 'y': '{randy_q3:600:900}', 'z': '{randz_patrolalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_q4:100:400}', 'y': '{randy_q4:600:900}', 'z': '{randz_patrolalt:12:18}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_along_path']
        },


        'extended_flight_distance': {
            'name': 'Extended Distance Flight Test',
            'description': 'Fly minimum distance to test endurance - uses history checks',
            'content': 'Drone {drone_name} performs extended distance flight test: take off to {randz_distalt:15:20} meters, fly a route that covers at least {randint_mindist:1000:1500} meters total distance. The route should include waypoints at ({randx_dist1:150:400}, {randy_dist1:150:400}, {randz_distalt:15:20}), ({randx_dist2:650:900}, {randy_dist2:150:400}, {randz_distalt:15:20}), ({randx_dist3:650:900}, {randy_dist3:650:900}, {randz_distalt:15:20}), and ({randx_dist4:150:400}, {randy_dist4:650:900}, {randz_distalt:15:20}). After completing the distance requirement, the mission concludes.',
            'content_aliases': [
                'Test {drone_name} endurance: fly at least {randint_mindist:1000:1500} meters at {randz_distalt:15:20}m altitude, visiting ({randx_dist1:150:400},{randy_dist1:150:400},{randz_distalt:15:20}), ({randx_dist2:650:900},{randy_dist2:150:400},{randz_distalt:15:20}), ({randx_dist3:650:900},{randy_dist3:650:900},{randz_distalt:15:20}), and ({randx_dist4:150:400},{randy_dist4:650:900},{randz_distalt:15:20}).',
                'Command {drone_name} to cover a minimum of {randint_mindist:1000:1500}m flight path at {randz_distalt:15:20} meters altitude, specifically through WP1:({randx_dist1:150:400},{randy_dist1:150:400},{randz_distalt:15:20}), WP2:({randx_dist2:650:900},{randy_dist2:150:400},{randz_distalt:15:20}), WP3:({randx_dist3:650:900},{randy_dist3:650:900},{randz_distalt:15:20}), WP4:({randx_dist4:150:400},{randy_dist4:650:900},{randz_distalt:15:20}).',
                '{drone_name} performs a long-range flight test: visit waypoints ({randx_dist1:150:400}, {randy_dist1:150:400}, {randz_distalt:15:20}), ({randx_dist2:650:900}, {randy_dist2:150:400}, {randz_distalt:15:20}), ({randx_dist3:650:900}, {randy_dist3:650:900}, {randz_distalt:15:20}), and ({randx_dist4:150:400}, {randy_dist4:650:900}, {randz_distalt:15:20}) to cover {randint_mindist:1000:1500}m+.',
                'Execute an extended flight for {drone_name} to surpass {randint_mindist:1000:1500}m distance, using the route ({randx_dist1:150:400},{randy_dist1:150:400},{randz_distalt:15:20}) -> ({randx_dist2:650:900},{randy_dist2:150:400},{randz_distalt:15:20}) -> ({randx_dist3:650:900},{randy_dist3:650:900},{randz_distalt:15:20}) -> ({randx_dist4:150:400},{randy_dist4:650:900},{randz_distalt:15:20}).',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_distalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_id}',
                    'waypoints': [
                        {'x': '{randx_dist1:150:400}', 'y': '{randy_dist1:150:400}', 'z': '{randz_distalt:15:20}'},
                        {'x': '{randx_dist2:650:900}', 'y': '{randy_dist2:150:400}', 'z': '{randz_distalt:15:20}'},
                        {'x': '{randx_dist3:650:900}', 'y': '{randy_dist3:650:900}', 'z': '{randz_distalt:15:20}'},
                        {'x': '{randx_dist4:150:400}', 'y': '{randy_dist4:650:900}', 'z': '{randz_distalt:15:20}'}
                    ]
                }}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_moved_distance',
                        'parameters': {'drone_id': '{drone_id}', 'min_distance': '{randint_mindist:200:300}'}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dist1:150:400}', 'y': '{randy_dist1:150:400}', 'z': '{randz_distalt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dist2:650:900}', 'y': '{randy_dist2:150:400}', 'z': '{randz_distalt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dist3:650:900}', 'y': '{randy_dist3:650:900}', 'z': '{randz_distalt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dist4:150:400}', 'y': '{randy_dist4:650:900}', 'z': '{randz_distalt:15:20}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_along_path']
        },


        'multi_target_reach_verification': {
            'name': 'Multi-Target Reach Verification',
            'description': 'Visit multiple targets with reach verification - complex checks',
            'content': 'Drone {drone_name} multi-target verification mission: take off to {randz_reach:16:22} meters, visit and reach targets {target_1_name} and {target_2_name}. Each target must be reached at least once to verify successful visits. Fly within target radius for each visit.',
            'content_aliases': [
                '{drone_name} visit {target_1_name} and {target_2_name} at altitude {randz_reach:16:22}m',
                'make drone {drone_name} take off to {randz_reach:16:22}m and verify reach of two targets: {target_1_name} and {target_2_name}',
                '{drone_name} multi-visit target verification mission at {randz_reach:16:22} meters for {target_1_name} and {target_2_name}',
                'drone {drone_name} dual target reach confirmation: fly at {randz_reach:16:22}m and enter both {target_1_name} and {target_2_name}',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_reach:16:22}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover']
        },

        'obstacle_avoidance_path': {
            'name': 'Obstacle Avoidance Navigation',
            'description': 'Navigate around obstacles to reach destination',
            'content': 'Drone {drone_name} takes off to {randz_avoid:18:25} meters altitude, navigates from start point ({randx_start:150:400}, {randy_start:150:400}, {randz_avoid:18:25}) to destination ({randx_dest:650:900}, {randy_dest:650:900}, {randz_avoid:18:25}) while avoiding obstacle {obstacle_name}. Must fly above obstacle height or around it. After reaching destination, land there.',
            'content_aliases': [
                'Navigate {drone_name} from ({randx_start:150:400},{randy_start:150:400}) to ({randx_dest:650:900},{randy_dest:650:900}) at {randz_avoid:18:25}m, avoiding {obstacle_name}, then land.',
                'Command {drone_name} to fly obstacle-aware path: takeoff to {randz_avoid:18:25}m, go to ({randx_start:150:400},{randy_start:150:400}), avoid {obstacle_name} en route to ({randx_dest:650:900},{randy_dest:650:900}), and land.',
                '{drone_name} mission: takeoff {randz_avoid:18:25}m, traverse from ({randx_start:150:400},{randy_start:150:400}) to destination ({randx_dest:650:900},{randy_dest:650:900}) bypassing {obstacle_name}, followed by landing.',
                'Execute safe passage for {drone_name}: start at ({randx_start:150:400},{randy_start:150:400}), fly to ({randx_dest:650:900},{randy_dest:650:900}) at {randz_avoid:18:25}m avoiding {obstacle_name}, and conclude with landing.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_avoid:18:25}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_start:150:400}', 'y': '{randy_start:150:400}', 'z': '{randz_avoid:18:25}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_dest:650:900}', 'y': '{randy_dest:650:900}', 'z': '{randz_avoid:18:25}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_start:150:400}', 'y': '{randy_start:150:400}', 'z': '{randz_avoid:18:25}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dest:650:900}', 'y': '{randy_dest:650:900}', 'z': '{randz_avoid:18:25}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_dest:650:900}', 'y': '{randy_dest:650:900}', 'z': 0, 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'land']
        },

        'complex_obstacle_course': {
            'name': 'Complex Obstacle Course Navigation',
            'description': 'Navigate through multiple obstacles to reach destination via waypoints',
            'content': 'Drone {drone_name} navigates complex obstacle course from start ({randx_coursestart:150:400}, {randy_coursestart:150:400}, {randz_course:15:20}) through waypoints ({randx_coursewp1:250:450}, {randy_coursewp1:250:450}, {randz_course:15:20}), ({randx_coursewp2:450:650}, {randy_coursewp2:250:450}, {randz_course:15:20}), ({randx_coursewp3:550:750}, {randy_coursewp3:450:650}, {randz_course:15:20}), ({randx_coursewp4:350:550}, {randy_coursewp4:550:700}, {randz_course:15:20}) to destination ({randx_courseend:650:900}, {randy_courseend:650:900}, {randz_course:15:20}). Course includes obstacles {obstacle_1_name}, {obstacle_2_name}, and {obstacle_3_name}. Must visit all waypoints in sequence while avoiding all obstacles, adjusting altitude as needed. Reach destination and land safely.',
            'content_aliases': [
                'Navigate {drone_name} through obstacle course at {randz_course:15:20}m: start ({randx_coursestart:150:400},{randy_coursestart:150:400},{randz_course:15:20}), then ({randx_coursewp1:250:450},{randy_coursewp1:250:450},{randz_course:15:20}), ({randx_coursewp2:450:650},{randy_coursewp2:250:450},{randz_course:15:20}), ({randx_coursewp3:550:750},{randy_coursewp3:450:650},{randz_course:15:20}), ({randx_coursewp4:350:550},{randy_coursewp4:550:700},{randz_course:15:20}), end ({randx_courseend:650:900},{randy_courseend:650:900},{randz_course:15:20}), avoiding {obstacle_1_name}, {obstacle_2_name}, {obstacle_3_name}, then land.',
                'Command {drone_name} to fly complex path at {randz_course:15:20}m from ({randx_coursestart:150:400},{randy_coursestart:150:400},{randz_course:15:20}) through WP1 ({randx_coursewp1:250:450},{randy_coursewp1:250:450},{randz_course:15:20}), WP2 ({randx_coursewp2:450:650},{randy_coursewp2:250:450},{randz_course:15:20}), WP3 ({randx_coursewp3:550:750},{randy_coursewp3:450:650},{randz_course:15:20}), WP4 ({randx_coursewp4:350:550},{randy_coursewp4:550:700},{randz_course:15:20}), then destination ({randx_courseend:650:900},{randy_courseend:650:900},{randz_course:15:20}), dodging {obstacle_1_name}, {obstacle_2_name}, {obstacle_3_name}.',
                '{drone_name} advanced navigation: begin at ({randx_coursestart:150:400},{randy_coursestart:150:400},{randz_course:15:20}), traverse ({randx_coursewp1:250:450},{randy_coursewp1:250:450},{randz_course:15:20}), ({randx_coursewp2:450:650},{randy_coursewp2:250:450},{randz_course:15:20}), ({randx_coursewp3:550:750},{randy_coursewp3:450:650},{randz_course:15:20}), ({randx_coursewp4:350:550},{randy_coursewp4:550:700},{randz_course:15:20}) amidst {obstacle_1_name}, {obstacle_2_name}, {obstacle_3_name}, then reach ({randx_courseend:650:900},{randy_courseend:650:900},{randz_course:15:20}) to land.',
                'Execute multi-leg mission with {drone_name}: takeoff {randz_course:15:20}m, start ({randx_coursestart:150:400},{randy_coursestart:150:400},{randz_course:15:20}), visit ({randx_coursewp1:250:450},{randy_coursewp1:250:450},{randz_course:15:20}) -> ({randx_coursewp2:450:650},{randy_coursewp2:250:450},{randz_course:15:20}) -> ({randx_coursewp3:550:750},{randy_coursewp3:450:650},{randz_course:15:20}) -> ({randx_coursewp4:350:550},{randy_coursewp4:550:700},{randz_course:15:20}), avoid {obstacle_1_name}, {obstacle_2_name}, {obstacle_3_name}, reach ({randx_courseend:650:900},{randy_courseend:650:900},{randz_course:15:20}), and land.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_coursestart:150:400}', 'y': '{randy_coursestart:150:400}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_coursewp1:250:450}', 'y': '{randy_coursewp1:250:450}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_coursewp2:450:650}', 'y': '{randy_coursewp2:250:450}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_coursewp3:550:750}', 'y': '{randy_coursewp3:450:650}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_coursewp4:350:550}', 'y': '{randy_coursewp4:550:700}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_courseend:650:900}', 'y': '{randy_courseend:650:900}', 'z': '{randz_course:15:20}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_coursewp1:250:450}', 'y': '{randy_coursewp1:250:450}', 'z': '{randz_course:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_coursewp2:450:650}', 'y': '{randy_coursewp2:250:450}', 'z': '{randz_course:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_coursewp3:550:750}', 'y': '{randy_coursewp3:450:650}', 'z': '{randz_course:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_coursewp4:350:550}', 'y': '{randy_coursewp4:550:700}', 'z': '{randz_course:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_courseend:650:900}', 'y': '{randy_courseend:650:900}', 'z': 0, 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path', 'change_altitude', 'land']
        },

        'flight_marathon_navigation': {
            'name': 'Flight Marathon Navigation',
            'description': 'Long-distance navigation through 10 intermediate waypoints',
            'content': 'Drone {drone_name} performs a marathon flight. Take off to {randz_mara:20:30} meters, fly to start point ({randx_start:100:200}, {randy_start:100:200}, {randz_mara}), then navigate through 10 waypoints: ({randx_wp1:200:300}, {randy_wp1:100:200}, {randz_mara}), ({randx_wp2:300:400}, {randy_wp2:200:300}, {randz_mara}), ({randx_wp3:400:500}, {randy_wp3:300:400}, {randz_mara}), ({randx_wp4:500:600}, {randy_wp4:400:500}, {randz_mara}), ({randx_wp5:600:700}, {randy_wp5:500:600}, {randz_mara}), ({randx_wp6:700:800}, {randy_wp6:600:700}, {randz_mara}), ({randx_wp7:800:900}, {randy_wp7:700:800}, {randz_mara}), ({randx_wp8:900:1000}, {randy_wp8:800:900}, {randz_mara}), ({randx_wp9:800:900}, {randy_wp9:100:200}, {randz_mara}), ({randx_wp10:100:200}, {randy_wp10:800:900}, {randz_mara}). Avoid obstacles {obstacle_1_name}, {obstacle_2_name}. Finally, fly to end point ({randx_end:500:600}, {randy_end:500:600}, {randz_mara}) and land.',
            'content_aliases': [
                'Command {drone_name} on a marathon route: take off to {randz_mara:20:30}m, start at ({randx_start:100:200},{randy_start:100:200},{randz_mara}), then clear WP1 ({randx_wp1:200:300},{randy_wp1:100:200},{randz_mara}), WP2 ({randx_wp2:300:400},{randy_wp2:200:300},{randz_mara}), WP3 ({randx_wp3:400:500},{randy_wp3:300:400},{randz_mara}), WP4 ({randx_wp4:500:600},{randy_wp4:400:500},{randz_mara}), WP5 ({randx_wp5:600:700},{randy_wp5:500:600},{randz_mara}), WP6 ({randx_wp6:700:800},{randy_wp6:600:700},{randz_mara}), WP7 ({randx_wp7:800:900},{randy_wp7:700:800},{randz_mara}), WP8 ({randx_wp8:900:1000},{randy_wp8:800:900},{randz_mara}), WP9 ({randx_wp9:800:900},{randy_wp9:100:200},{randz_mara}), WP10 ({randx_wp10:100:200},{randy_wp10:800:900},{randz_mara}), avoid {obstacle_1_name} and {obstacle_2_name}, finish at ({randx_end:500:600},{randy_end:500:600},{randz_mara}), and land.',
                '{drone_name} endurance navigation: lift to {randz_mara:20:30} meters, begin at ({randx_start:100:200},{randy_start:100:200},{randz_mara}), fly sequentially through ({randx_wp1:200:300},{randy_wp1:100:200},{randz_mara}), ({randx_wp2:300:400},{randy_wp2:200:300},{randz_mara}), ({randx_wp3:400:500},{randy_wp3:300:400},{randz_mara}), ({randx_wp4:500:600},{randy_wp4:400:500},{randz_mara}), ({randx_wp5:600:700},{randy_wp5:500:600},{randz_mara}), ({randx_wp6:700:800},{randy_wp6:600:700},{randz_mara}), ({randx_wp7:800:900},{randy_wp7:700:800},{randz_mara}), ({randx_wp8:900:1000},{randy_wp8:800:900},{randz_mara}), ({randx_wp9:800:900},{randy_wp9:100:200},{randz_mara}), ({randx_wp10:100:200},{randy_wp10:800:900},{randz_mara}), route around {obstacle_1_name} and {obstacle_2_name}, then reach ({randx_end:500:600},{randy_end:500:600},{randz_mara}) and land.'
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_start:100:200}', 'y': '{randy_start:100:200}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp1:200:300}', 'y': '{randy_wp1:100:200}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp2:300:400}', 'y': '{randy_wp2:200:300}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp3:400:500}', 'y': '{randy_wp3:300:400}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp4:500:600}', 'y': '{randy_wp4:400:500}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp5:600:700}', 'y': '{randy_wp5:500:600}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp6:700:800}', 'y': '{randy_wp6:600:700}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp7:800:900}', 'y': '{randy_wp7:700:800}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp8:900:1000}', 'y': '{randy_wp8:800:900}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp9:800:900}', 'y': '{randy_wp9:100:200}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_wp10:100:200}', 'y': '{randy_wp10:800:900}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_end:500:600}', 'y': '{randy_end:500:600}', 'z': '{randz_mara:20:30}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_start:100:200}', 'y': '{randy_start:100:200}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp1:200:300}', 'y': '{randy_wp1:100:200}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp2:300:400}', 'y': '{randy_wp2:200:300}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp3:400:500}', 'y': '{randy_wp3:300:400}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp4:500:600}', 'y': '{randy_wp4:400:500}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp5:600:700}', 'y': '{randy_wp5:500:600}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp6:700:800}', 'y': '{randy_wp6:600:700}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp7:800:900}', 'y': '{randy_wp7:700:800}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp8:900:1000}', 'y': '{randy_wp8:800:900}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp9:800:900}', 'y': '{randy_wp9:100:200}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_wp10:100:200}', 'y': '{randy_wp10:800:900}', 'z': '{randz_mara:20:30}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_end:500:600}', 'y': '{randy_end:500:600}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}}
                ]
            },
            'commands': ['take_off', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'land']
        },

        'extreme_flight_marathon_navigation': {
            'name': 'Extreme Flight Marathon Navigation',
            'description': 'Extreme long-distance zigzag navigation through 20 intermediate waypoints across the full map',
            'content': 'Drone {drone_name} performs an extreme marathon flight. Take off to {randz_extmara:24:34} meters, fly to start point ({randx_extstart:50:120}, {randy_extstart:50:120}, {randz_extmara}), then zigzag across the full map through 20 intermediate waypoints: ({randx_extwp1:80:160}, {randy_extwp1:120:200}, {randz_extmara}), ({randx_extwp2:840:940}, {randy_extwp2:120:220}, {randz_extmara}), ({randx_extwp3:120:220}, {randy_extwp3:220:320}, {randz_extmara}), ({randx_extwp4:780:900}, {randy_extwp4:260:360}, {randz_extmara}), ({randx_extwp5:80:200}, {randy_extwp5:360:460}, {randz_extmara}), ({randx_extwp6:820:960}, {randy_extwp6:420:520}, {randz_extmara}), ({randx_extwp7:120:240}, {randy_extwp7:520:620}, {randz_extmara}), ({randx_extwp8:760:900}, {randy_extwp8:580:680}, {randz_extmara}), ({randx_extwp9:80:180}, {randy_extwp9:680:780}, {randz_extmara}), ({randx_extwp10:840:960}, {randy_extwp10:740:840}, {randz_extmara}), ({randx_extwp11:140:260}, {randy_extwp11:820:920}, {randz_extmara}), ({randx_extwp12:760:900}, {randy_extwp12:860:960}, {randz_extmara}), ({randx_extwp13:420:520}, {randy_extwp13:760:860}, {randz_extmara}), ({randx_extwp14:900:980}, {randy_extwp14:520:640}, {randz_extmara}), ({randx_extwp15:40:140}, {randy_extwp15:520:640}, {randz_extmara}), ({randx_extwp16:900:980}, {randy_extwp16:320:440}, {randz_extmara}), ({randx_extwp17:40:140}, {randy_extwp17:300:420}, {randz_extmara}), ({randx_extwp18:720:860}, {randy_extwp18:80:180}, {randz_extmara}), ({randx_extwp19:260:380}, {randy_extwp19:860:960}, {randz_extmara}), ({randx_extwp20:600:760}, {randy_extwp20:420:540}, {randz_extmara}). Avoid obstacles {obstacle_1_name}, {obstacle_2_name}, and {obstacle_3_name}. Finally, fly to end point ({randx_extend:880:960}, {randy_extend:880:960}, {randz_extmara}) and land.',
            'content_aliases': [
                'Command {drone_name} on an extreme zigzag marathon at {randz_extmara:24:34}m: start ({randx_extstart:50:120},{randy_extstart:50:120},{randz_extmara}), then visit ({randx_extwp1:80:160},{randy_extwp1:120:200},{randz_extmara}), ({randx_extwp2:840:940},{randy_extwp2:120:220},{randz_extmara}), ({randx_extwp3:120:220},{randy_extwp3:220:320},{randz_extmara}), ({randx_extwp4:780:900},{randy_extwp4:260:360},{randz_extmara}), ({randx_extwp5:80:200},{randy_extwp5:360:460},{randz_extmara}), ({randx_extwp6:820:960},{randy_extwp6:420:520},{randz_extmara}), ({randx_extwp7:120:240},{randy_extwp7:520:620},{randz_extmara}), ({randx_extwp8:760:900},{randy_extwp8:580:680},{randz_extmara}), ({randx_extwp9:80:180},{randy_extwp9:680:780},{randz_extmara}), ({randx_extwp10:840:960},{randy_extwp10:740:840},{randz_extmara}), ({randx_extwp11:140:260},{randy_extwp11:820:920},{randz_extmara}), ({randx_extwp12:760:900},{randy_extwp12:860:960},{randz_extmara}), ({randx_extwp13:420:520},{randy_extwp13:760:860},{randz_extmara}), ({randx_extwp14:900:980},{randy_extwp14:520:640},{randz_extmara}), ({randx_extwp15:40:140},{randy_extwp15:520:640},{randz_extmara}), ({randx_extwp16:900:980},{randy_extwp16:320:440},{randz_extmara}), ({randx_extwp17:40:140},{randy_extwp17:300:420},{randz_extmara}), ({randx_extwp18:720:860},{randy_extwp18:80:180},{randz_extmara}), ({randx_extwp19:260:380},{randy_extwp19:860:960},{randz_extmara}), ({randx_extwp20:600:760},{randy_extwp20:420:540},{randz_extmara}), avoid {obstacle_1_name}, {obstacle_2_name}, {obstacle_3_name}, finish at ({randx_extend:880:960},{randy_extend:880:960},{randz_extmara}), and land.',
                '{drone_name} full-map endurance route: take off to {randz_extmara:24:34} meters and fly from ({randx_extstart:50:120},{randy_extstart:50:120},{randz_extmara}) through the 20-point sequence ({randx_extwp1:80:160},{randy_extwp1:120:200},{randz_extmara}) -> ({randx_extwp2:840:940},{randy_extwp2:120:220},{randz_extmara}) -> ({randx_extwp3:120:220},{randy_extwp3:220:320},{randz_extmara}) -> ({randx_extwp4:780:900},{randy_extwp4:260:360},{randz_extmara}) -> ({randx_extwp5:80:200},{randy_extwp5:360:460},{randz_extmara}) -> ({randx_extwp6:820:960},{randy_extwp6:420:520},{randz_extmara}) -> ({randx_extwp7:120:240},{randy_extwp7:520:620},{randz_extmara}) -> ({randx_extwp8:760:900},{randy_extwp8:580:680},{randz_extmara}) -> ({randx_extwp9:80:180},{randy_extwp9:680:780},{randz_extmara}) -> ({randx_extwp10:840:960},{randy_extwp10:740:840},{randz_extmara}) -> ({randx_extwp11:140:260},{randy_extwp11:820:920},{randz_extmara}) -> ({randx_extwp12:760:900},{randy_extwp12:860:960},{randz_extmara}) -> ({randx_extwp13:420:520},{randy_extwp13:760:860},{randz_extmara}) -> ({randx_extwp14:900:980},{randy_extwp14:520:640},{randz_extmara}) -> ({randx_extwp15:40:140},{randy_extwp15:520:640},{randz_extmara}) -> ({randx_extwp16:900:980},{randy_extwp16:320:440},{randz_extmara}) -> ({randx_extwp17:40:140},{randy_extwp17:300:420},{randz_extmara}) -> ({randx_extwp18:720:860},{randy_extwp18:80:180},{randz_extmara}) -> ({randx_extwp19:260:380},{randy_extwp19:860:960},{randz_extmara}) -> ({randx_extwp20:600:760},{randy_extwp20:420:540},{randz_extmara}), avoid {obstacle_1_name}, {obstacle_2_name}, and {obstacle_3_name}, then reach ({randx_extend:880:960},{randy_extend:880:960},{randz_extmara}) and land.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extstart:50:120}', 'y': '{randy_extstart:50:120}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp1:80:160}', 'y': '{randy_extwp1:120:200}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp2:840:940}', 'y': '{randy_extwp2:120:220}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp3:120:220}', 'y': '{randy_extwp3:220:320}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp4:780:900}', 'y': '{randy_extwp4:260:360}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp5:80:200}', 'y': '{randy_extwp5:360:460}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp6:820:960}', 'y': '{randy_extwp6:420:520}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp7:120:240}', 'y': '{randy_extwp7:520:620}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp8:760:900}', 'y': '{randy_extwp8:580:680}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp9:80:180}', 'y': '{randy_extwp9:680:780}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp10:840:960}', 'y': '{randy_extwp10:740:840}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp11:140:260}', 'y': '{randy_extwp11:820:920}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp12:760:900}', 'y': '{randy_extwp12:860:960}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp13:420:520}', 'y': '{randy_extwp13:760:860}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp14:900:980}', 'y': '{randy_extwp14:520:640}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp15:40:140}', 'y': '{randy_extwp15:520:640}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp16:900:980}', 'y': '{randy_extwp16:320:440}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp17:40:140}', 'y': '{randy_extwp17:300:420}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp18:720:860}', 'y': '{randy_extwp18:80:180}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp19:260:380}', 'y': '{randy_extwp19:860:960}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extwp20:600:760}', 'y': '{randy_extwp20:420:540}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_extend:880:960}', 'y': '{randy_extend:880:960}', 'z': '{randz_extmara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extstart:50:120}', 'y': '{randy_extstart:50:120}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp1:80:160}', 'y': '{randy_extwp1:120:200}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp2:840:940}', 'y': '{randy_extwp2:120:220}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp3:120:220}', 'y': '{randy_extwp3:220:320}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp4:780:900}', 'y': '{randy_extwp4:260:360}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp5:80:200}', 'y': '{randy_extwp5:360:460}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp6:820:960}', 'y': '{randy_extwp6:420:520}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp7:120:240}', 'y': '{randy_extwp7:520:620}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp8:760:900}', 'y': '{randy_extwp8:580:680}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp9:80:180}', 'y': '{randy_extwp9:680:780}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp10:840:960}', 'y': '{randy_extwp10:740:840}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp11:140:260}', 'y': '{randy_extwp11:820:920}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp12:760:900}', 'y': '{randy_extwp12:860:960}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp13:420:520}', 'y': '{randy_extwp13:760:860}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp14:900:980}', 'y': '{randy_extwp14:520:640}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp15:40:140}', 'y': '{randy_extwp15:520:640}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp16:900:980}', 'y': '{randy_extwp16:320:440}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp17:40:140}', 'y': '{randy_extwp17:300:420}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp18:720:860}', 'y': '{randy_extwp18:80:180}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp19:260:380}', 'y': '{randy_extwp19:860:960}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extwp20:600:760}', 'y': '{randy_extwp20:420:540}', 'z': '{randz_extmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_id}', 'x': '{randx_extend:880:960}', 'y': '{randy_extend:880:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}}
                ]
            },
            'commands': ['take_off', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'move_to', 'land']
        },

        'dual_flight_marathon_navigation': {
            'name': 'Dual Flight Marathon Navigation',
            'description': 'Two drones each navigate 10 intermediate marathon waypoints',
            'content': 'Drones {drone_1_name} and {drone_2_name} perform a dual marathon flight at {randz_dualmara:20:30} meters. {drone_1_name} route: fly to and start at ({randx_dualmarad1start:50:120}, {randy_dualmarad1start:50:120}, {randz_dualmara}), then waypoints ({randx_dualmarad1wp1:100:200}, {randy_dualmarad1wp1:120:220}, {randz_dualmara}), ({randx_dualmarad1wp2:800:940}, {randy_dualmarad1wp2:160:260}, {randz_dualmara}), ({randx_dualmarad1wp3:120:240}, {randy_dualmarad1wp3:260:360}, {randz_dualmara}), ({randx_dualmarad1wp4:760:900}, {randy_dualmarad1wp4:360:460}, {randz_dualmara}), ({randx_dualmarad1wp5:80:200}, {randy_dualmarad1wp5:460:560}, {randz_dualmara}), ({randx_dualmarad1wp6:820:960}, {randy_dualmarad1wp6:540:640}, {randz_dualmara}), ({randx_dualmarad1wp7:120:240}, {randy_dualmarad1wp7:620:720}, {randz_dualmara}), ({randx_dualmarad1wp8:760:900}, {randy_dualmarad1wp8:680:760}, {randz_dualmara}), ({randx_dualmarad1wp9:240:380}, {randy_dualmarad1wp9:760:900}, {randz_dualmara}), ({randx_dualmarad1wp10:620:780}, {randy_dualmarad1wp10:820:960}, {randz_dualmara}), then end ({randx_dualmarad1end:860:960}, {randy_dualmarad1end:860:960}, {randz_dualmara}) and land. {drone_2_name} route: fly to and start at  ({randx_dualmarad2start:880:960}, {randy_dualmarad2start:50:120}, {randz_dualmara}), then waypoints ({randx_dualmarad2wp1:820:940}, {randy_dualmarad2wp1:120:220}, {randz_dualmara}), ({randx_dualmarad2wp2:80:220}, {randy_dualmarad2wp2:160:260}, {randz_dualmara}), ({randx_dualmarad2wp3:780:920}, {randy_dualmarad2wp3:260:360}, {randz_dualmara}), ({randx_dualmarad2wp4:100:240}, {randy_dualmarad2wp4:360:460}, {randz_dualmara}), ({randx_dualmarad2wp5:820:960}, {randy_dualmarad2wp5:460:560}, {randz_dualmara}), ({randx_dualmarad2wp6:80:220}, {randy_dualmarad2wp6:540:640}, {randz_dualmara}), ({randx_dualmarad2wp7:760:920}, {randy_dualmarad2wp7:620:720}, {randz_dualmara}), ({randx_dualmarad2wp8:120:280}, {randy_dualmarad2wp8:680:760}, {randz_dualmara}), ({randx_dualmarad2wp9:700:860}, {randy_dualmarad2wp9:760:900}, {randz_dualmara}), ({randx_dualmarad2wp10:260:420}, {randy_dualmarad2wp10:820:960}, {randz_dualmara}), then end ({randx_dualmarad2end:50:140}, {randy_dualmarad2end:860:960}, {randz_dualmara}) and land.',
            'content_aliases': [
                'Dual marathon routes at {randz_dualmara}m: {drone_1_name} fly to and start at  ({randx_dualmarad1start:50:120},{randy_dualmarad1start:50:120}) -> ({randx_dualmarad1wp1:100:200},{randy_dualmarad1wp1:120:220}) -> ({randx_dualmarad1wp2:800:940},{randy_dualmarad1wp2:160:260}) -> ({randx_dualmarad1wp3:120:240},{randy_dualmarad1wp3:260:360}) -> ({randx_dualmarad1wp4:760:900},{randy_dualmarad1wp4:360:460}) -> ({randx_dualmarad1wp5:80:200},{randy_dualmarad1wp5:460:560}) -> ({randx_dualmarad1wp6:820:960},{randy_dualmarad1wp6:540:640}) -> ({randx_dualmarad1wp7:120:240},{randy_dualmarad1wp7:620:720}) -> ({randx_dualmarad1wp8:760:900},{randy_dualmarad1wp8:680:760}) -> ({randx_dualmarad1wp9:240:380},{randy_dualmarad1wp9:760:900}) -> ({randx_dualmarad1wp10:620:780},{randy_dualmarad1wp10:820:960}) -> end ({randx_dualmarad1end:860:960},{randy_dualmarad1end:860:960}); {drone_2_name} fly to and start at ({randx_dualmarad2start:880:960},{randy_dualmarad2start:50:120}) -> ({randx_dualmarad2wp1:820:940},{randy_dualmarad2wp1:120:220}) -> ({randx_dualmarad2wp2:80:220},{randy_dualmarad2wp2:160:260}) -> ({randx_dualmarad2wp3:780:920},{randy_dualmarad2wp3:260:360}) -> ({randx_dualmarad2wp4:100:240},{randy_dualmarad2wp4:360:460}) -> ({randx_dualmarad2wp5:820:960},{randy_dualmarad2wp5:460:560}) -> ({randx_dualmarad2wp6:80:220},{randy_dualmarad2wp6:540:640}) -> ({randx_dualmarad2wp7:760:920},{randy_dualmarad2wp7:620:720}) -> ({randx_dualmarad2wp8:120:280},{randy_dualmarad2wp8:680:760}) -> ({randx_dualmarad2wp9:700:860},{randy_dualmarad2wp9:760:900}) -> ({randx_dualmarad2wp10:260:420},{randy_dualmarad2wp10:820:960}) -> end ({randx_dualmarad2end:50:140},{randy_dualmarad2end:860:960}); both drones land.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1start:50:120}', 'y': '{randy_dualmarad1start:50:120}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp1:100:200}', 'y': '{randy_dualmarad1wp1:120:220}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp2:800:940}', 'y': '{randy_dualmarad1wp2:160:260}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp3:120:240}', 'y': '{randy_dualmarad1wp3:260:360}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp4:760:900}', 'y': '{randy_dualmarad1wp4:360:460}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp5:80:200}', 'y': '{randy_dualmarad1wp5:460:560}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp6:820:960}', 'y': '{randy_dualmarad1wp6:540:640}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp7:120:240}', 'y': '{randy_dualmarad1wp7:620:720}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp8:760:900}', 'y': '{randy_dualmarad1wp8:680:760}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp9:240:380}', 'y': '{randy_dualmarad1wp9:760:900}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1wp10:620:780}', 'y': '{randy_dualmarad1wp10:820:960}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_dualmarad1end:860:960}', 'y': '{randy_dualmarad1end:860:960}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2start:880:960}', 'y': '{randy_dualmarad2start:50:120}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp1:820:940}', 'y': '{randy_dualmarad2wp1:120:220}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp2:80:220}', 'y': '{randy_dualmarad2wp2:160:260}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp3:780:920}', 'y': '{randy_dualmarad2wp3:260:360}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp4:100:240}', 'y': '{randy_dualmarad2wp4:360:460}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp5:820:960}', 'y': '{randy_dualmarad2wp5:460:560}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp6:80:220}', 'y': '{randy_dualmarad2wp6:540:640}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp7:760:920}', 'y': '{randy_dualmarad2wp7:620:720}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp8:120:280}', 'y': '{randy_dualmarad2wp8:680:760}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp9:700:860}', 'y': '{randy_dualmarad2wp9:760:900}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2wp10:260:420}', 'y': '{randy_dualmarad2wp10:820:960}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_dualmarad2end:50:140}', 'y': '{randy_dualmarad2end:860:960}', 'z': '{randz_dualmara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1start:50:120}', 'y': '{randy_dualmarad1start:50:120}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp1:100:200}', 'y': '{randy_dualmarad1wp1:120:220}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp2:800:940}', 'y': '{randy_dualmarad1wp2:160:260}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp3:120:240}', 'y': '{randy_dualmarad1wp3:260:360}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp4:760:900}', 'y': '{randy_dualmarad1wp4:360:460}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp5:80:200}', 'y': '{randy_dualmarad1wp5:460:560}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp6:820:960}', 'y': '{randy_dualmarad1wp6:540:640}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp7:120:240}', 'y': '{randy_dualmarad1wp7:620:720}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp8:760:900}', 'y': '{randy_dualmarad1wp8:680:760}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp9:240:380}', 'y': '{randy_dualmarad1wp9:760:900}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1wp10:620:780}', 'y': '{randy_dualmarad1wp10:820:960}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_dualmarad1end:860:960}', 'y': '{randy_dualmarad1end:860:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_1_id}', 'tolerance': 0.5}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2start:880:960}', 'y': '{randy_dualmarad2start:50:120}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp1:820:940}', 'y': '{randy_dualmarad2wp1:120:220}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp2:80:220}', 'y': '{randy_dualmarad2wp2:160:260}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp3:780:920}', 'y': '{randy_dualmarad2wp3:260:360}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp4:100:240}', 'y': '{randy_dualmarad2wp4:360:460}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp5:820:960}', 'y': '{randy_dualmarad2wp5:460:560}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp6:80:220}', 'y': '{randy_dualmarad2wp6:540:640}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp7:760:920}', 'y': '{randy_dualmarad2wp7:620:720}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp8:120:280}', 'y': '{randy_dualmarad2wp8:680:760}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp9:700:860}', 'y': '{randy_dualmarad2wp9:760:900}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2wp10:260:420}', 'y': '{randy_dualmarad2wp10:820:960}', 'z': '{randz_dualmara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_dualmarad2end:50:140}', 'y': '{randy_dualmarad2end:860:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_2_id}', 'tolerance': 0.5}}
                ]
            },
            'commands': ['take_off', 'move_to', 'land']
        },

        'triple_flight_marathon_navigation': {
            'name': 'Triple Flight Marathon Navigation',
            'description': 'Three drones each navigate 10 intermediate marathon waypoints',
            'content': 'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} perform a triple marathon flight at {randz_trimara:20:30} meters. {drone_1_name} route: fly to and start at  ({randx_trimarad1start:50:120}, {randy_trimarad1start:80:160}, {randz_trimara}), then waypoints ({randx_trimarad1wp1:100:220}, {randy_trimarad1wp1:140:220}, {randz_trimara}), ({randx_trimarad1wp2:780:940}, {randy_trimarad1wp2:180:260}, {randz_trimara}), ({randx_trimarad1wp3:120:260}, {randy_trimarad1wp3:260:340}, {randz_trimara}), ({randx_trimarad1wp4:760:920}, {randy_trimarad1wp4:340:420}, {randz_trimara}), ({randx_trimarad1wp5:100:240}, {randy_trimarad1wp5:420:500}, {randz_trimara}), ({randx_trimarad1wp6:800:960}, {randy_trimarad1wp6:500:580}, {randz_trimara}), ({randx_trimarad1wp7:120:260}, {randy_trimarad1wp7:580:660}, {randz_trimara}), ({randx_trimarad1wp8:760:920}, {randy_trimarad1wp8:660:740}, {randz_trimara}), ({randx_trimarad1wp9:180:340}, {randy_trimarad1wp9:740:860}, {randz_trimara}), ({randx_trimarad1wp10:620:800}, {randy_trimarad1wp10:820:960}, {randz_trimara}), then end ({randx_trimarad1end:860:960}, {randy_trimarad1end:860:960}, {randz_trimara}) and land. {drone_2_name} route: fly to and start at  ({randx_trimarad2start:460:560}, {randy_trimarad2start:50:140}, {randz_trimara}), then waypoints ({randx_trimarad2wp1:420:540}, {randy_trimarad2wp1:140:220}, {randz_trimara}), ({randx_trimarad2wp2:850:960}, {randy_trimarad2wp2:220:300}, {randz_trimara}), ({randx_trimarad2wp3:60:180}, {randy_trimarad2wp3:300:380}, {randz_trimara}), ({randx_trimarad2wp4:840:960}, {randy_trimarad2wp4:380:460}, {randz_trimara}), ({randx_trimarad2wp5:80:200}, {randy_trimarad2wp5:460:540}, {randz_trimara}), ({randx_trimarad2wp6:820:940}, {randy_trimarad2wp6:540:620}, {randz_trimara}), ({randx_trimarad2wp7:80:220}, {randy_trimarad2wp7:620:700}, {randz_trimara}), ({randx_trimarad2wp8:780:920}, {randy_trimarad2wp8:700:780}, {randz_trimara}), ({randx_trimarad2wp9:260:420}, {randy_trimarad2wp9:780:900}, {randz_trimara}), ({randx_trimarad2wp10:520:700}, {randy_trimarad2wp10:820:960}, {randz_trimara}), then end ({randx_trimarad2end:440:580}, {randy_trimarad2end:860:960}, {randz_trimara}) and land. {drone_3_name} route: fly to and start at  ({randx_trimarad3start:880:960}, {randy_trimarad3start:80:160}, {randz_trimara}), then waypoints ({randx_trimarad3wp1:800:940}, {randy_trimarad3wp1:140:220}, {randz_trimara}), ({randx_trimarad3wp2:100:240}, {randy_trimarad3wp2:180:260}, {randz_trimara}), ({randx_trimarad3wp3:780:920}, {randy_trimarad3wp3:260:340}, {randz_trimara}), ({randx_trimarad3wp4:120:260}, {randy_trimarad3wp4:340:420}, {randz_trimara}), ({randx_trimarad3wp5:780:940}, {randy_trimarad3wp5:420:500}, {randz_trimara}), ({randx_trimarad3wp6:100:240}, {randy_trimarad3wp6:500:580}, {randz_trimara}), ({randx_trimarad3wp7:760:920}, {randy_trimarad3wp7:580:660}, {randz_trimara}), ({randx_trimarad3wp8:120:280}, {randy_trimarad3wp8:660:740}, {randz_trimara}), ({randx_trimarad3wp9:700:860}, {randy_trimarad3wp9:740:860}, {randz_trimara}), ({randx_trimarad3wp10:240:420}, {randy_trimarad3wp10:820:960}, {randz_trimara}), then end ({randx_trimarad3end:50:140}, {randy_trimarad3end:860:960}, {randz_trimara}) and land.',
            'content_aliases': [
                'Triple marathon routes at {randz_trimara}m: {drone_1_name} fly to and start at  ({randx_trimarad1start:50:120},{randy_trimarad1start:80:160}) -> ({randx_trimarad1wp1:100:220},{randy_trimarad1wp1:140:220}) -> ({randx_trimarad1wp2:780:940},{randy_trimarad1wp2:180:260}) -> ({randx_trimarad1wp3:120:260},{randy_trimarad1wp3:260:340}) -> ({randx_trimarad1wp4:760:920},{randy_trimarad1wp4:340:420}) -> ({randx_trimarad1wp5:100:240},{randy_trimarad1wp5:420:500}) -> ({randx_trimarad1wp6:800:960},{randy_trimarad1wp6:500:580}) -> ({randx_trimarad1wp7:120:260},{randy_trimarad1wp7:580:660}) -> ({randx_trimarad1wp8:760:920},{randy_trimarad1wp8:660:740}) -> ({randx_trimarad1wp9:180:340},{randy_trimarad1wp9:740:860}) -> ({randx_trimarad1wp10:620:800},{randy_trimarad1wp10:820:960}) -> end ({randx_trimarad1end:860:960},{randy_trimarad1end:860:960}); {drone_2_name} fly to and start at  ({randx_trimarad2start:460:560},{randy_trimarad2start:50:140}) -> ({randx_trimarad2wp1:420:540},{randy_trimarad2wp1:140:220}) -> ({randx_trimarad2wp2:850:960},{randy_trimarad2wp2:220:300}) -> ({randx_trimarad2wp3:60:180},{randy_trimarad2wp3:300:380}) -> ({randx_trimarad2wp4:840:960},{randy_trimarad2wp4:380:460}) -> ({randx_trimarad2wp5:80:200},{randy_trimarad2wp5:460:540}) -> ({randx_trimarad2wp6:820:940},{randy_trimarad2wp6:540:620}) -> ({randx_trimarad2wp7:80:220},{randy_trimarad2wp7:620:700}) -> ({randx_trimarad2wp8:780:920},{randy_trimarad2wp8:700:780}) -> ({randx_trimarad2wp9:260:420},{randy_trimarad2wp9:780:900}) -> ({randx_trimarad2wp10:520:700},{randy_trimarad2wp10:820:960}) -> end ({randx_trimarad2end:440:580},{randy_trimarad2end:860:960}); {drone_3_name} fly to and start at  ({randx_trimarad3start:880:960},{randy_trimarad3start:80:160}) -> ({randx_trimarad3wp1:800:940},{randy_trimarad3wp1:140:220}) -> ({randx_trimarad3wp2:100:240},{randy_trimarad3wp2:180:260}) -> ({randx_trimarad3wp3:780:920},{randy_trimarad3wp3:260:340}) -> ({randx_trimarad3wp4:120:260},{randy_trimarad3wp4:340:420}) -> ({randx_trimarad3wp5:780:940},{randy_trimarad3wp5:420:500}) -> ({randx_trimarad3wp6:100:240},{randy_trimarad3wp6:500:580}) -> ({randx_trimarad3wp7:760:920},{randy_trimarad3wp7:580:660}) -> ({randx_trimarad3wp8:120:280},{randy_trimarad3wp8:660:740}) -> ({randx_trimarad3wp9:700:860},{randy_trimarad3wp9:740:860}) -> ({randx_trimarad3wp10:240:420},{randy_trimarad3wp10:820:960}) -> end ({randx_trimarad3end:50:140},{randy_trimarad3end:860:960}); all drones land.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Navigation',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1start:50:120}', 'y': '{randy_trimarad1start:80:160}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp1:100:220}', 'y': '{randy_trimarad1wp1:140:220}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp2:780:940}', 'y': '{randy_trimarad1wp2:180:260}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp3:120:260}', 'y': '{randy_trimarad1wp3:260:340}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp4:760:920}', 'y': '{randy_trimarad1wp4:340:420}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp5:100:240}', 'y': '{randy_trimarad1wp5:420:500}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp6:800:960}', 'y': '{randy_trimarad1wp6:500:580}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp7:120:260}', 'y': '{randy_trimarad1wp7:580:660}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp8:760:920}', 'y': '{randy_trimarad1wp8:660:740}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp9:180:340}', 'y': '{randy_trimarad1wp9:740:860}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1wp10:620:800}', 'y': '{randy_trimarad1wp10:820:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_trimarad1end:860:960}', 'y': '{randy_trimarad1end:860:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2start:460:560}', 'y': '{randy_trimarad2start:50:140}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp1:420:540}', 'y': '{randy_trimarad2wp1:140:220}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp2:850:960}', 'y': '{randy_trimarad2wp2:220:300}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp3:60:180}', 'y': '{randy_trimarad2wp3:300:380}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp4:840:960}', 'y': '{randy_trimarad2wp4:380:460}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp5:80:200}', 'y': '{randy_trimarad2wp5:460:540}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp6:820:940}', 'y': '{randy_trimarad2wp6:540:620}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp7:80:220}', 'y': '{randy_trimarad2wp7:620:700}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp8:780:920}', 'y': '{randy_trimarad2wp8:700:780}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp9:260:420}', 'y': '{randy_trimarad2wp9:780:900}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2wp10:520:700}', 'y': '{randy_trimarad2wp10:820:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_trimarad2end:440:580}', 'y': '{randy_trimarad2end:860:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3start:880:960}', 'y': '{randy_trimarad3start:80:160}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp1:800:940}', 'y': '{randy_trimarad3wp1:140:220}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp2:100:240}', 'y': '{randy_trimarad3wp2:180:260}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp3:780:920}', 'y': '{randy_trimarad3wp3:260:340}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp4:120:260}', 'y': '{randy_trimarad3wp4:340:420}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp5:780:940}', 'y': '{randy_trimarad3wp5:420:500}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp6:100:240}', 'y': '{randy_trimarad3wp6:500:580}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp7:760:920}', 'y': '{randy_trimarad3wp7:580:660}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp8:120:280}', 'y': '{randy_trimarad3wp8:660:740}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp9:700:860}', 'y': '{randy_trimarad3wp9:740:860}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3wp10:240:420}', 'y': '{randy_trimarad3wp10:820:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_trimarad3end:50:140}', 'y': '{randy_trimarad3end:860:960}', 'z': '{randz_trimara}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_3_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {'endpoint': '/check/drone_has_moved_distance', 'parameters': {'drone_id': '{drone_1_id}', 'min_distance': 1500}},
                    {'endpoint': '/check/drone_has_moved_distance', 'parameters': {'drone_id': '{drone_2_id}', 'min_distance': 1500}},
                    {'endpoint': '/check/drone_has_moved_distance', 'parameters': {'drone_id': '{drone_3_id}', 'min_distance': 1500}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp1:100:220}', 'y': '{randy_trimarad1wp1:140:220}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp2:780:940}', 'y': '{randy_trimarad1wp2:180:260}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp3:120:260}', 'y': '{randy_trimarad1wp3:260:340}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp4:760:920}', 'y': '{randy_trimarad1wp4:340:420}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp5:100:240}', 'y': '{randy_trimarad1wp5:420:500}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp6:800:960}', 'y': '{randy_trimarad1wp6:500:580}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp7:120:260}', 'y': '{randy_trimarad1wp7:580:660}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp8:760:920}', 'y': '{randy_trimarad1wp8:660:740}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp9:180:340}', 'y': '{randy_trimarad1wp9:740:860}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1wp10:620:800}', 'y': '{randy_trimarad1wp10:820:960}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_trimarad1end:860:960}', 'y': '{randy_trimarad1end:860:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_1_id}', 'tolerance': 0.5}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp1:420:540}', 'y': '{randy_trimarad2wp1:140:220}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp2:850:960}', 'y': '{randy_trimarad2wp2:220:300}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp3:60:180}', 'y': '{randy_trimarad2wp3:300:380}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp4:840:960}', 'y': '{randy_trimarad2wp4:380:460}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp5:80:200}', 'y': '{randy_trimarad2wp5:460:540}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp6:820:940}', 'y': '{randy_trimarad2wp6:540:620}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp7:80:220}', 'y': '{randy_trimarad2wp7:620:700}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp8:780:920}', 'y': '{randy_trimarad2wp8:700:780}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp9:260:420}', 'y': '{randy_trimarad2wp9:780:900}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2wp10:520:700}', 'y': '{randy_trimarad2wp10:820:960}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_trimarad2end:440:580}', 'y': '{randy_trimarad2end:860:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_2_id}', 'tolerance': 0.5}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp1:800:940}', 'y': '{randy_trimarad3wp1:140:220}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp2:100:240}', 'y': '{randy_trimarad3wp2:180:260}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp3:780:920}', 'y': '{randy_trimarad3wp3:260:340}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp4:120:260}', 'y': '{randy_trimarad3wp4:340:420}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp5:780:940}', 'y': '{randy_trimarad3wp5:420:500}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp6:100:240}', 'y': '{randy_trimarad3wp6:500:580}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp7:760:920}', 'y': '{randy_trimarad3wp7:580:660}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp8:120:280}', 'y': '{randy_trimarad3wp8:660:740}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp9:700:860}', 'y': '{randy_trimarad3wp9:740:860}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_has_visited_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3wp10:240:420}', 'y': '{randy_trimarad3wp10:820:960}', 'z': '{randz_trimara}', 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_position', 'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_trimarad3end:50:140}', 'y': '{randy_trimarad3end:860:960}', 'z': 0, 'tolerance': 3.0}},
                    {'endpoint': '/check/drone_on_ground', 'parameters': {'drone_id': '{drone_3_id}', 'tolerance': 0.5}}
                ]
            },
            'commands': ['take_off', 'move_to', 'land']
        },

    # ===== Search =====

        'search_task_with_photo': {
            'name': 'Search Task with Photo',
            'description': 'Move to specific coordinates and capture photos',
            'content': 'Drone {drone_name} must take off to {randz_survalt:18:25} meters, fly to position ({randx_surv}, {randy_surv}, {randz_survalt:18:25}), hover at that location, and take a photo.',
            'content_aliases': [
                'Drone {drone_name} takeoff {randz_survalt:18:25}m, go to ({randx_surv},{randy_surv}), hover and take photo',
                'Search mission: drone {drone_name} to position x={randx_surv} y={randy_surv} z={randz_survalt:18:25}, capture photo',
                'make drone {drone_name} fly to coordinates ({randx_surv}, {randy_surv}) at altitude {randz_survalt:18:25} meters and take picture',
                'Drone {drone_name} reconnaissance at ({randx_surv},{randy_surv},{randz_survalt:18:25}) with photo capture',
            ],
            'difficulty': 'easy',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_survalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_surv}', 'y': '{randy_surv}', 'z': '{randz_survalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_surv}', 'y': '{randy_surv}', 'z': '{randz_survalt:18:25}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_id}', 'min_count': 1}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover', 'take_photo']
        },

        'target_inspection': {
            'name': 'Target Inspection',
            'description': 'Drone finds and photographs a target',
            'content': 'Drone {drone_name} must take off to {random_inspectalt:15:20} meters, navigate to target {target_name}, and take a photo.',
            'content_aliases': [
                'Send {drone_name} to locate {target_name} at {random_inspectalt:15:20}m altitude and capture photograph',
                'Deploy drone {drone_name} for target {target_name} photography mission at elevation {random_inspectalt:15:20} meters',
                '{drone_name} reconnaissance task: take off to {random_inspectalt:15:20}m, find and photograph {target_name}',
                'Assign {drone_name} to survey {target_name} at {random_inspectalt:15:20} meters and document with photo',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_inspectalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'take_photo']
        },

        'hover_observation_mission': {
            'name': 'Extended Hover Observation',
            'description': 'Hover at location for extended period - uses history checks',
            'content': 'Drone {drone_name} stationary observation mission: take off to {randz_hover:18:25} meters, fly to observation point ({randx_hover:400:650}, {randy_hover:400:650}, {randz_hover}), hover at this position for at least {randint_hoverdur:10:20} seconds while maintaining position.',
            'content_aliases': [
                'Have {drone_name} ascend to {randz_hover:18:25}m, move to ({randx_hover:400:650}, {randy_hover:400:650}, {randz_hover}), and hold that spot for at least {randint_hoverdur:10:20} seconds.',
                '{drone_name} performs a stationary watch: take off to {randz_hover:18:25} meters, proceed to ({randx_hover:400:650}, {randy_hover:400:650}, {randz_hover}), then hover in place for {randint_hoverdur:10:20}+ seconds.',
                'Execute an observation hover with {drone_name}: climb to {randz_hover:18:25}m, fly to ({randx_hover:400:650}, {randy_hover:400:650}, {randz_hover}), and maintain position for at least {randint_hoverdur:10:20} seconds.',
                'Station-keeping mission for {drone_name}: take off to {randz_hover:18:25} meters, travel to ({randx_hover:400:650}, {randy_hover:400:650}, {randz_hover}), and hover there for a minimum of {randint_hoverdur:10:20} seconds.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_hover}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_hover}', 'y': '{randy_hover}', 'z': '{randz_hover}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}', 'duration': '{randint_hoverdur}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_hovered',
                        'parameters': {'drone_id': '{drone_id}', 'min_duration': '{randint_hoverdur}'}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_hover}', 'y': '{randy_hover}', 'z': '{randz_hover}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover']
        },

        'photo_documentation_mission': {
            'name': 'Photo Documentation Mission',
            'description': 'Take multiple photos at various waypoints - uses history checks',
            'content': 'Drone {drone_name} performs photo documentation mission: take off to {randz_photoalt:15:20} meters, visit three waypoints at ({randx_photo1:150:400}, {randy_photo1:150:400}, {randz_photoalt:15:20}), ({randx_photo2:400:650}, {randy_photo2:400:650}, {randz_photoalt:15:20}), and ({randx_photo3:650:900}, {randy_photo3:650:900}, {randz_photoalt:15:20}). At each waypoint, take a photo.',
            'content_aliases': [
                '{drone_name} needs to capture photos at three locations: ({randx_photo1:150:400}, {randy_photo1:150:400}), ({randx_photo2:400:650}, {randy_photo2:400:650}), and ({randx_photo3:650:900}, {randy_photo3:650:900}) at {randz_photoalt:15:20}m altitude.',
                'Send {drone_name} to photograph waypoints ({randx_photo1:150:400}, {randy_photo1:150:400}), ({randx_photo2:400:650}, {randy_photo2:400:650}), and ({randx_photo3:650:900}, {randy_photo3:650:900}) maintaining {randz_photoalt:15:20}m height.',
                'Execute photo mission with {drone_name}: visit ({randx_photo1:150:400}, {randy_photo1:150:400}, {randz_photoalt:15:20}), ({randx_photo2:400:650}, {randy_photo2:400:650}, {randz_photoalt:15:20}), and ({randx_photo3:650:900}, {randy_photo3:650:900}, {randz_photoalt:15:20}) to take pictures.',
                'Task {drone_name} to fly to ({randx_photo1:150:400}, {randy_photo1:150:400}), ({randx_photo2:400:650}, {randy_photo2:400:650}), and ({randx_photo3:650:900}, {randy_photo3:650:900}) at {randz_photoalt:15:20}m and perform photo documentation at each spot.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_photoalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_photo1:150:400}', 'y': '{randy_photo1:150:400}', 'z': '{randz_photoalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_photo2:400:650}', 'y': '{randy_photo2:400:650}', 'z': '{randz_photoalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_photo3:650:900}', 'y': '{randy_photo3:650:900}', 'z': '{randz_photoalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_id}', 'min_count': 3}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_photo1:150:400}', 'y': '{randy_photo1:150:400}', 'z': '{randz_photoalt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_photo2:400:650}', 'y': '{randy_photo2:400:650}', 'z': '{randz_photoalt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_photo3:650:900}', 'y': '{randy_photo3:650:900}', 'z': '{randz_photoalt:15:20}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'take_photo']
        },



        'multiple_target_inspection': {
            'name': 'Multiple Target Inspection',
            'description': 'One drone finds and photographs two targets',
            'content': 'Drone {drone_name} must take off to {random_multitargetalt:16:22} meters, navigate to target {target_1_name}, take a photo, then navigate to target {target_2_name} and take another photo.',
            'content_aliases': [
                'Have {drone_name} take off to {random_multitargetalt:16:22}m, reach {target_1_name} for a photo, then proceed to {target_2_name} for a second photo.',
                '{drone_name} dual-target inspection: climb to {random_multitargetalt:16:22} meters, visit {target_1_name} and {target_2_name} in sequence, and capture a photo at each.',
                'Deploy {drone_name} to photograph {target_1_name} then {target_2_name} after takeoff to {random_multitargetalt:16:22}m altitude.',
                'Two-target survey for {drone_name}: take off to {random_multitargetalt:16:22}m, navigate to {target_1_name} for imaging, then image {target_2_name}.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_multitargetalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'take_photo', 'move_to', 'take_photo']
        },

        'multi_target_sequential': {
            'name': 'Sequential Multi-Target Visit',
            'description': 'Visit multiple targets in optimal sequence',
            'content': 'Drone {drone_name} performs sequential multi-target mission: take off to {random_seqalt:18:25} meters, visit targets {target_1_name}, {target_2_name}, and {target_3_name} in sequence. At each target, get within the target radius, hover for observation, and take a photo. Plan optimal route to minimize flight distance.',
            'content_aliases': [
                'Have {drone_name} climb to {random_seqalt:18:25}m and visit {target_1_name}, {target_2_name}, {target_3_name} in order; at each, enter the target radius, hover to observe, and capture a photo while following the shortest route.',
                '{drone_name} sequential inspection run: take off to {random_seqalt:18:25} meters, proceed {target_1_name} → {target_2_name} → {target_3_name}, and for each target hover within range and take a photo, optimizing the path length.',
                'Plan an efficient three-target tour for {drone_name} at {random_seqalt:18:25}m: visit {target_1_name}, then {target_2_name}, then {target_3_name}, hovering inside each target radius for observation and photo capture.',
                'Sequential coverage for {drone_name}: ascend to {random_seqalt:18:25}m, reach {target_1_name}, {target_2_name}, {target_3_name} in order, hover at each to observe, and take a photo while minimizing travel distance.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_seqalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_3_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover', 'take_photo']
        },


        'area_coverage_search': {
            'name': 'Complete Area Coverage Search',
            'description': 'Systematically search and cover a target area completely',
            'content': 'Drone {drone_name} executes comprehensive area search of {target_name}. Take off to {random_coveralt:20:25} meters and perform a systematic coverage pattern to search at least 95% of the target area using an efficient pattern.',
            'content_aliases': [
                'Task {drone_name} to perform a 95% coverage search of {target_name} at {random_coveralt:20:25}m altitude',
                'Execute systematic search with {drone_name} over {target_name} at {random_coveralt:20:25}m, ensuring 95% area coverage',
                '{drone_name} mission: scan {target_name} completely (95%+) using an efficient pattern at {random_coveralt:20:25} meters',
                'Deploy {drone_name} for comprehensive 95% sweep of {target_name} at {random_coveralt:20:25}m',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_coveralt:20:25}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_id}', 'coverage_threshold': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

        'dual_drone_area_coverage_search': {
            'name': 'Dual Drone Area Coverage Search',
            'description': 'Two drones coordinate to search and cover one target area',
            'content': 'Drones {drone_1_name} and {drone_2_name} execute a coordinated area coverage search of {target_name}. Both take off to {random_dualcoveralt:20:25} meters and divide the target area into complementary search sectors, using efficient grid or serpentine paths to achieve at least 95% total area coverage.',
            'content_aliases': [
                'Task {drone_1_name} and {drone_2_name} to perform a shared 95% coverage search of {target_name} at {random_dualcoveralt:20:25}m altitude.',
                'Execute systematic two-drone search over {target_name} with {drone_1_name} and {drone_2_name} at {random_dualcoveralt:20:25}m, ensuring 95% area coverage.',
                'Coordinate {drone_1_name} and {drone_2_name} to scan {target_name} completely (95%+) using complementary coverage paths at {random_dualcoveralt:20:25} meters.',
                'Deploy {drone_1_name} and {drone_2_name} for a comprehensive 95% sweep of {target_name}, splitting the area coverage work at {random_dualcoveralt:20:25}m.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_dualcoveralt:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_dualcoveralt:20:25}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_dualcoveralt:20:25}', 'max_altitude': '{random_dualcoveralt:20:25}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_dualcoveralt:20:25}', 'max_altitude': '{random_dualcoveralt:20:25}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_id}', 'coverage_threshold': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

        'triple_drone_area_coverage_search': {
            'name': 'Triple Drone Area Coverage Search',
            'description': 'Three drones coordinate to search and cover one target area',
            'content': 'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} execute a coordinated area coverage search of {target_name}. All drones take off to {random_tricoveralt:20:25} meters and divide the target area into three complementary search sectors, using efficient grid or serpentine paths to achieve at least 95% total area coverage.',
            'content_aliases': [
                'Task {drone_1_name}, {drone_2_name}, and {drone_3_name} to perform a shared 95% coverage search of {target_name} at {random_tricoveralt:20:25}m altitude.',
                'Execute systematic three-drone search over {target_name} with {drone_1_name}, {drone_2_name}, and {drone_3_name} at {random_tricoveralt:20:25}m, ensuring 95% area coverage.',
                'Coordinate {drone_1_name}, {drone_2_name}, and {drone_3_name} to scan {target_name} completely (95%+) using complementary coverage paths at {random_tricoveralt:20:25} meters.',
                'Deploy {drone_1_name}, {drone_2_name}, and {drone_3_name} for a comprehensive 95% sweep of {target_name}, splitting the area coverage work at {random_tricoveralt:20:25}m.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_tricoveralt:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_tricoveralt:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{random_tricoveralt:20:25}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_tricoveralt:20:25}', 'max_altitude': '{random_tricoveralt:20:25}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_tricoveralt:20:25}', 'max_altitude': '{random_tricoveralt:20:25}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_altitude': '{random_tricoveralt:20:25}', 'max_altitude': '{random_tricoveralt:20:25}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_id}', 'coverage_threshold': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

        'any_drone_area_coverage_search': {
            'name': 'Any Drone Area Coverage Search',
            'description': 'Search and cover one target area without assigning a specific drone',
            'content': 'Use any available drone or drones to execute a comprehensive area coverage search of {target_name}. Search the target area with an efficient grid, spiral, or serpentine pattern until at least 95% of the target area is covered.',
            'content_aliases': [
                'Perform a 95% coverage search of {target_name} using any available drone or drones.',
                'Search {target_name} without assigning a specific drone, ensuring at least 95% area coverage.',
                'Use available drones as needed to scan {target_name} completely (95%+) with an efficient coverage pattern.',
                'Complete a flexible-drone coverage sweep of {target_name}, reaching at least 95% searched area.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_id}', 'coverage_threshold': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

        'any_drone_two_target_area_coverage_search': {
            'name': 'Any Drone Two-Target Area Coverage Search',
            'description': 'Search and cover two target areas without assigning specific drones',
            'content': 'Use any available drone or drones to execute comprehensive area coverage searches of {target_1_name} and {target_2_name}. Cover both target areas with efficient grid, spiral, or serpentine patterns until each target reaches at least 95% area coverage.',
            'content_aliases': [
                'Perform 95% coverage searches of {target_1_name} and {target_2_name} using any available drone or drones.',
                'Search {target_1_name} and {target_2_name} without assigning specific drones, ensuring at least 95% area coverage for each target.',
                'Use available drones as needed to scan both {target_1_name} and {target_2_name} completely (95%+) with efficient coverage patterns.',
                'Complete flexible-drone coverage sweeps of {target_1_name} and {target_2_name}, reaching at least 95% searched area on both.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_1_id}', 'coverage_threshold': 0.95}
                    },
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_2_id}', 'coverage_threshold': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

        'target_area_full_coverage': {
            'name': 'Target Area Complete Coverage and Photography Mission',
            'description': 'Achieve 99% coverage of target area - complex check logic',
            'content': 'Drone {drone_name} comprehensive area coverage mission: take off to {random_covermissionalt:18:25} meters altitude, perform systematic coverage of target {target_name} to achieve at least 99% area coverage. Use efficient search pattern (grid, spiral, or serpentine). Take at least 3 photos periodically for documentation. Continue coverage until 99% threshold is met or exceeded.',
            'content_aliases': [
                'Command {drone_name} to achieve 99% search coverage of {target_name} at {random_covermissionalt:18:25}m with at least 3 periodic photos',
                '{drone_name} full area scan: cover 99% of {target_name} at {random_covermissionalt:18:25} meters using systematic pattern and photography for taking 3 photos',
                'Initiate high-coverage search (99%) of {target_name} with {drone_name} at {random_covermissionalt:18:25}m, documenting with at least 3 photos',
                'Task {drone_name} with complete 99% sweep of {target_name} at {random_covermissionalt:18:25}m altitude including at least 3 photos capture',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_covermissionalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_fully_searched',
                        'parameters': {'target_id': '{target_id}', 'coverage_threshold': 0.99}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_id}', 'min_count': 3}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path', 'take_photo']
        },

        'area_search_task_completion': {
            'name': 'Area Search Task Completion',
            'description': 'Perform area search work until 95% session task progress is reached',
            'content': 'Take off necessary drones and search the assigned area targets with systematic coverage patterns until the session task progress exceeds 95%.',
            'content_aliases': [
                'Launch the required drones and perform area coverage searches until overall session progress passes 95%.',
                'Use available drones to search the assigned areas with efficient coverage patterns until task progress exceeds 95%.',
                'Continue area search operations across the session until the task progress is above 95%.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Search',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/task_progress',
                        'parameters': {'expected_progress': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path']
        },

    # ===== Tracking =====
        'adaptive_search_and_track': {
            'name': 'Adaptive Search and Track Moving Target',
            'description': 'Search for and continuously track a moving target',
            'content': 'Drone {drone_name} performs adaptive search and track mission for moving target {target_name}. Take off to {random_trackalt:18:25} meters, locate the moving target using search pattern, then maintain tracking by staying within the target perception radius as it moves. Track for at least 60 seconds or until target is reached {randint_times:2:6}+ times.',
            'content_aliases': [
                'Have {drone_name} ascend to {random_trackalt:18:25}m, search for moving target {target_name}, then keep within its perception radius while tracking for at least 60 seconds or until it is reached {randint_times:2:6}+ times.',
                '{drone_name} adaptive pursuit: take off to {random_trackalt:18:25} meters, locate {target_name} via a search pattern, and maintain close tracking until 60 seconds pass or the target is reached {randint_times:2:6}+ times.',
                'Execute a moving-target track with {drone_name}: climb to {random_trackalt:18:25}m, find {target_name}, and keep it in range while tracking for 60+ seconds or {randint_times:2:6}+ reaches.',
                'Dynamic search-and-track for {drone_name}: take off to {random_trackalt:18:25}m, acquire {target_name}, then stay within perception radius to track for at least 60 seconds or {randint_times:2:6}+ reaches.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Tracking',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['target_tracking'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_trackalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_reached_drone_number',
                        'parameters': {'target_id': '{target_id}', 'expected_count': '{randint_times:2:6}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },

        

    # ===== Delivery =====
        'delivery_mission': {
            'name': 'Delivery to Specific Location',
            'description': 'Navigate to pickup and delivery locations',
            'content': 'Drone {drone_name} should take off to {randz_deliveryalt:12:18} meters altitude, fly to pickup point at ({randx_pickup:150:400}, {randy_pickup:150:350}, {randz_deliveryalt:12:18}), land to collect goods, then take off again to {randz_deliveryalt:12:18} meters, fly to delivery point at ({randx_delivery:550:850}, {randy_delivery:400:650}, {randz_deliveryalt:12:18}), and land to complete delivery.',
            'content_aliases': [
                '{drone_name} delivery mission: pick up from ({randx_pickup:150:400},{randy_pickup:150:350}) on ground and deliver to ({randx_delivery:550:850},{randy_delivery:400:650}) at {randz_deliveryalt:12:18}m, then land.',
                'drone {drone_name} takes off to {randz_deliveryalt:12:18}m, collects package on ground at position {randx_pickup:150:400},{randy_pickup:150:350}, then delivers to {randx_delivery:550:850},{randy_delivery:400:650} at {randz_deliveryalt:12:18}m and final land.',
                'make {drone_name} pick up goods at ({randx_pickup:150:400},{randy_pickup:150:350},{randz_deliveryalt:12:18}) , land to pick up, and carry to ({randx_delivery:550:850},{randy_delivery:400:650},{randz_deliveryalt:12:18}), then land to drop off',
                '{drone_name} transport mission from pickup point ({randx_pickup:150:400},{randy_pickup:150:350}) to delivery coordinates ({randx_delivery:550:850},{randy_delivery:400:650}) at altitude {randz_deliveryalt:12:18} meters',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Delivery',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_deliveryalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_pickup:150:400}', 'y': '{randy_pickup:150:350}', 'z': '{randz_deliveryalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_deliveryalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_delivery:550:850}', 'y': '{randy_delivery:400:650}', 'z': '{randz_deliveryalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_pickup:150:400}', 'y': '{randy_pickup:150:350}', 'z': 0, 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_delivery:550:850}', 'y': '{randy_delivery:400:650}', 'z': 0, 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'land', 'take_off', 'move_to', 'land']
        },

        'multi_waypoint_delivery': {
            'name': 'Multi-Waypoint Delivery Route',
            'description': 'Deliver packages to three waypoints in sequence with landings',
            'content': 'Drone {drone_name} executes delivery route: take off to {randz_mwdalt:15:20} meters, fly to waypoint 1 at ({randx_mwd1:200:400}, {randy_mwd1:200:350}, {randz_mwdalt:15:20}) and land to deliver. Then take off, fly to waypoint 2 at ({randx_mwd2:500:700}, {randy_mwd2:200:350}, {randz_mwdalt:15:20}) and land. Finally take off, fly to waypoint 3 at ({randx_mwd3:500:700}, {randy_mwd3:450:600}, {randz_mwdalt:15:20}) and land to complete the mission.',
            'content_aliases': [
                'Execute three-stop delivery circuit with {drone_name}: take off to {randz_mwdalt:15:20}m, land at ({randx_mwd1:200:400},{randy_mwd1:200:350},{randz_mwdalt:15:20}), take off, land at ({randx_mwd2:500:700},{randy_mwd2:200:350},{randz_mwdalt:15:20}), take off, land at ({randx_mwd3:500:700},{randy_mwd3:450:600},{randz_mwdalt:15:20}).',
                '{drone_name} multi-stop delivery: fly at {randz_mwdalt:15:20}m, visit and land at ({randx_mwd1:200:400},{randy_mwd1:200:350},{randz_mwdalt:15:20}), then ({randx_mwd2:500:700},{randy_mwd2:200:350},{randz_mwdalt:15:20}), then ({randx_mwd3:500:700},{randy_mwd3:450:600},{randz_mwdalt:15:20}).',
                'Task {drone_name} to deliver to 3 locations at {randz_mwdalt:15:20}m: ({randx_mwd1:200:400},{randy_mwd1:200:350},{randz_mwdalt:15:20}), ({randx_mwd2:500:700},{randy_mwd2:200:350},{randz_mwdalt:15:20}), ({randx_mwd3:500:700},{randy_mwd3:450:600},{randz_mwdalt:15:20}), landing at each one.',
                'Sequential delivery run for {drone_name}: use altitude {randz_mwdalt:15:20}m and land at WP1 ({randx_mwd1:200:400},{randy_mwd1:200:350},{randz_mwdalt:15:20}), WP2 ({randx_mwd2:500:700},{randy_mwd2:200:350},{randz_mwdalt:15:20}), and WP3 ({randx_mwd3:500:700},{randy_mwd3:450:600},{randz_mwdalt:15:20}).',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Delivery',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_mwd1:200:400}', 'y': '{randy_mwd1:200:350}', 'z': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_mwd2:500:700}', 'y': '{randy_mwd2:200:350}', 'z': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_id}', 'x': '{randx_mwd3:500:700}', 'y': '{randy_mwd3:450:600}', 'z': '{randz_mwdalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_mwd1:200:400}', 'y': '{randy_mwd1:200:350}', 'z': 0, 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_mwd2:500:700}', 'y': '{randy_mwd2:200:350}', 'z': 0, 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_id}', 'x': '{randx_mwd3:500:700}', 'y': '{randy_mwd3:450:600}', 'z': 0, 'tolerance': 1.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'land', 'take_off', 'move_to', 'land', 'take_off', 'move_to', 'land']
        },

    # ===== Battery Management =====
        'battery_management': {
            'name': 'Battery Management Mission',
            'description': 'Monitor battery and return before critical level',
            'content': 'Drone {drone_name} performs extended patrol: take off to {randz_battalt:15:20} meters, patrol rectangular area with corners ({randx_batt1:150:400}, {randy_batt1:150:400}), ({randx_batt2:650:900}, {randy_batt1:150:400}), ({randx_batt2:650:900}, {randy_batt2:650:900}), ({randx_batt1:150:400}, {randy_batt2:650:900}) at altitude {randz_battalt:15:20}m. Monitor battery throughout mission. Return home when battery drops below 30% or mission complete, then land.',
            'content_aliases': [
                'Assign {drone_name} to an extended patrol at {randz_battalt:15:20}m, covering the area from ({randx_batt1:150:400}, {randy_batt1:150:400}) to ({randx_batt2:650:900}, {randy_batt2:650:900}), with critical battery monitoring and automatic return at 30% charge.',
                'Task {drone_name} with continuous area search at {randz_battalt:15:20} meters, patrolling between ({randx_batt1:150:400}, {randy_batt1:150:400}) and ({randx_batt2:650:900}, {randy_batt2:650:900}), ensuring RTH if battery drops below 30%.',
                '{drone_name} performs an endurance mission at {randz_battalt:15:20}m, patrolling the region defined by ({randx_batt1:150:400}, {randy_batt1:150:400}) and ({randx_batt2:650:900}, {randy_batt2:650:900}), prioritizing battery longevity and safe return home.',
                'Manage {drone_name} for prolonged operation at {randz_battalt:15:20} meters, sweeping the area between ({randx_batt1:150:400}, {randy_batt1:150:400}) and ({randx_batt2:650:900}, {randy_batt2:650:900}), initiating return_home protocol upon low battery detection.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Battery Management',
            'is_builtin': True,
            'exclude_in_random_generation': True,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{randz_battalt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_id}',
                    'waypoints': [
                        {'x': '{randx_batt1:150:400}', 'y': '{randy_batt1:150:400}', 'z': '{randz_battalt:15:20}'},
                        {'x': '{randx_batt2:650:900}', 'y': '{randy_batt1:150:400}', 'z': '{randz_battalt:15:20}'},
                        {'x': '{randx_batt2:650:900}', 'y': '{randy_batt2:650:900}', 'z': '{randz_battalt:15:20}'},
                        {'x': '{randx_batt1:150:400}', 'y': '{randy_batt2:650:900}', 'z': '{randz_battalt:15:20}'}
                    ]
                }},
                {'endpoint': '/drones/{id}/command/return_home', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_battery_level',
                        'parameters': {'drone_id': '{drone_id}', 'min_level': 20.0}
                    },
                    {
                        'endpoint': '/check/drone_at_home',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_on_ground',
                        'parameters': {'drone_id': '{drone_id}', 'tolerance': 0.5}
                    }
                ]
            },
            'commands': ['take_off', 'move_along_path', 'return_home', 'land']
        },

        'charging_station_visit': {
            'name': 'Charging Station Visit',
            'description': 'Visit charging station and recharge',
            'content': 'Drone {drone_name} low battery recovery mission: take off to {random_chargealt:12:18} meters, navigate to nearest charging station (waypoint target), land at the station, charge battery by at least {randint_chargeamt:20:40} percent, then take off again.',
            'content_aliases': [
                '{drone_name} needs to take off to {random_chargealt:12:18}m, visit charging station, land, recharge by {randint_chargeamt:20:40}%, then take off again',
                'Send {drone_name} for a battery boost: ascend to {random_chargealt:12:18} meters, fly to charging station, land, charge by {randint_chargeamt:20:40}%, then take off.',
                '{drone_name} execute battery recovery: ascend to {random_chargealt:12:18}m, proceed to charging station, land, charge to {randint_chargeamt:20:40}%+, then re-launch.',
                'Task {drone_name} with an essential charge stop: fly at {random_chargealt:12:18}m to nearest power source, land, secure {randint_chargeamt:20:40}% charge, and prepare for flight.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Battery Management',
            'is_builtin': True,
            'exclude_in_random_generation': True,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_chargealt:12:18}'}},
                {'endpoint': '/drones/{id}/command/land', 'parameters': {'id': '{drone_id}'}},
                {'endpoint': '/drones/{id}/command/charge', 'parameters': {'id': '{drone_id}', 'charge_amount': '{randint_chargeamt:20:40}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_chargealt:12:18}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_charged',
                        'parameters': {'drone_id': '{drone_id}', 'min_charge_amount': '{randint_chargeamt:20:40}'}
                    },
                    {
                        'endpoint': '/check/drone_battery_level',
                        'parameters': {'drone_id': '{drone_id}', 'min_level': 50.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'land', 'charge']
        }, 

    # ===== Communication =====
        'communication_relay_mission': {
            'name': 'Communication Relay with Messages',
            'description': 'Send messages between drones - uses message history checks',
            'content': 'Communication relay mission: Drone {drone_1_name} acts as communication relay. Take off to {randz_commalt:18:25} meters, position at relay point ({randx_comm:400:650}, {randy_comm:400:650}, {randz_commalt:18:25}). Send broadcast messages to coordinate with other drones. Send at least {randint_cntmess:3:5} messages total during the mission.',
            'content_aliases': [
                '{drone_1_name} to establish relay at ({randx_comm:400:650}, {randy_comm:400:650}) altitude {randz_commalt:18:25}m and broadcast {randint_cntmess:3:5}+ coordination messages.',
                'Deploy {drone_1_name} as a message hub: fly to {randx_comm:400:650},{randy_comm:400:650} at {randz_commalt:18:25}m and transmit at least {randint_cntmess:3:5} broadcasts.',
                'Mission for {drone_1_name}: reach relay coordinates ({randx_comm:400:650}, {randy_comm:400:650}, {randz_commalt:18:25}) and send multiple broadcast alerts (min {randint_cntmess:3:5}).',
                'Set up comms link with {drone_1_name} at position {randx_comm:400:650},{randy_comm:400:650},{randz_commalt:18:25} and issue {randint_cntmess:3:5} fleet-wide messages.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Communication',
            'is_builtin': True,
            'exclude_in_random_generation': True,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_commalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_comm:400:650}', 'y': '{randy_comm:400:650}', 'z': '{randz_commalt:18:25}'}},
                {'endpoint': '/drones/{id}/command/broadcast', 'parameters': {'id': '{drone_1_id}', 'message': 'Relay station active'}},
                {'endpoint': '/drones/{id}/command/broadcast', 'parameters': {'id': '{drone_1_id}', 'message': 'Coordination message'}},
                {'endpoint': '/drones/{id}/command/broadcast', 'parameters': {'id': '{drone_1_id}', 'message': 'Mission update'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_sent_message',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_count': '{randint_cntmess:3:5}'}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_comm:400:650}', 'y': '{randy_comm:400:650}', 'z': '{randz_commalt:18:25}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'broadcast']
        },



    # ===== Multi-Drone Coordination =====
        'dual_patrol': {
            'name': 'Dual Drone Patrol',
            'description': 'Two drones patrol opposite sides of an area',
            'content': 'Drones {drone_1_name} and {drone_2_name} execute coordinated patrol. Both take off to {randz_dualalt:12:18} meters. {drone_1_name} patrols the route through waypoints ({randx_nstart:150:400},{randy_nstart:350:600},{randz_dualalt:12:18}), ({randx_nend:650:900},{randy_nend:350:600},{randz_dualalt:12:18}) while {drone_2_name} patrols the route through waypoints ({randx_sstart:150:400},{randy_sstart:150:400},{randz_dualalt:12:18}), ({randx_send:650:900},{randy_send:150:400},{randz_dualalt:12:18}).',
            'content_aliases': [
                'Have {drone_1_name} and {drone_2_name} take off to {randz_dualalt:12:18}m; {drone_1_name} patrols from ({randx_nstart:150:400},{randy_nstart:350:600},{randz_dualalt:12:18}) to ({randx_nend:650:900},{randy_nend:350:600},{randz_dualalt:12:18}) while {drone_2_name} patrols from ({randx_sstart:150:400},{randy_sstart:150:400},{randz_dualalt:12:18}) to ({randx_send:650:900},{randy_send:150:400},{randz_dualalt:12:18}).',
                'Dual patrol at {randz_dualalt:12:18}m: {drone_1_name} follows north route ({randx_nstart:150:400},{randy_nstart:350:600},{randz_dualalt:12:18}) -> ({randx_nend:650:900},{randy_nend:350:600},{randz_dualalt:12:18}); {drone_2_name} follows south route ({randx_sstart:150:400},{randy_sstart:150:400},{randz_dualalt:12:18}) -> ({randx_send:650:900},{randy_send:150:400},{randz_dualalt:12:18}).',
                'Launch {drone_1_name} and {drone_2_name} to {randz_dualalt:12:18}m and run parallel paths: north ({randx_nstart:150:400},{randy_nstart:350:600},{randz_dualalt:12:18}) to ({randx_nend:650:900},{randy_nend:350:600},{randz_dualalt:12:18}), south ({randx_sstart:150:400},{randy_sstart:150:400},{randz_dualalt:12:18}) to ({randx_send:650:900},{randy_send:150:400},{randz_dualalt:12:18}).',
                'Coordinated split patrol at {randz_dualalt:12:18}m: {drone_1_name} runs northern leg ({randx_nstart:150:400},{randy_nstart:350:600},{randz_dualalt:12:18}) -> ({randx_nend:650:900},{randy_nend:350:600},{randz_dualalt:12:18}); {drone_2_name} runs southern leg ({randx_sstart:150:400},{randy_sstart:150:400},{randz_dualalt:12:18}) -> ({randx_send:650:900},{randy_send:150:400},{randz_dualalt:12:18}).',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_dualalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_dualalt:12:18}'}},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_1_id}',
                    'waypoints': [
                        {'x': '{randx_nstart:150:400}', 'y': '{randy_nstart:350:600}', 'z': '{randz_dualalt:12:18}'},
                        {'x': '{randx_nend:650:900}', 'y': '{randy_nend:350:600}', 'z': '{randz_dualalt:12:18}'}
                    ]
                }},
                {'endpoint': '/drones/{id}/command/move_along_path', 'parameters': {
                    'id': '{drone_2_id}',
                    'waypoints': [
                        {'x': '{randx_sstart:150:400}', 'y': '{randy_sstart:150:400}', 'z': '{randz_dualalt:12:18}'},
                        {'x': '{randx_send:650:900}', 'y': '{randy_send:150:400}', 'z': '{randz_dualalt:12:18}'}
                    ]
                }}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_nstart:150:400}', 'y': '{randy_nstart:350:600}', 'z': '{randz_dualalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_nend:650:900}', 'y': '{randy_nend:350:600}', 'z': '{randz_dualalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_sstart:150:400}', 'y': '{randy_sstart:150:400}', 'z': '{randz_dualalt:12:18}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_send:650:900}', 'y': '{randy_send:150:400}', 'z': '{randz_dualalt:12:18}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_along_path']
        },

        'formation_line': {
            'name': 'Line Formation - 2 Drones',
            'description': 'Two drones maintain line formation',
            'content': 'Drones {drone_1_name} and {drone_2_name} form a line formation: both take off to {randz_linealt:15:20} meters. {drone_1_name} positions at ({randx_line:400:650}, {randy_line:400:650}, {randz_linealt:15:20}) and {drone_2_name} flys to ({randx_line2:400:650}, {randy_line2:400:650}, {randz_linealt:15:20}) first, and then move to {random_spacing:15:25} meters at most to {drone_1_name}. Both maintain formation for monitoring.',
            'content_aliases': [
                'Have {drone_1_name} and {drone_2_name} take off to {randz_linealt:15:20}m, set {drone_1_name} at ({randx_line:400:650},{randy_line:400:650},{randz_linealt:15:20}) and {drone_2_name} at ({randx_line2:400:650},{randy_line2:400:650},{randz_linealt:15:20}), then fly within a {random_spacing:15:25}m gap.',
                'Line formation at {randz_linealt:15:20}m: {drone_1_name} holds ({randx_line:400:650},{randy_line:400:650},{randz_linealt:15:20}) while {drone_2_name} trails at ({randx_line2:400:650},{randy_line2:400:650},{randz_linealt:15:20}) , then fly within {random_spacing:15:25}m separation.',
                'Two-drone line: climb to {randz_linealt:15:20}m and align {drone_1_name} at ({randx_line:400:650},{randy_line:400:650},{randz_linealt:15:20}) with {drone_2_name} at ({randx_line2:400:650},{randy_line2:400:650},{randz_linealt:15:20}), then within a {random_spacing:15:25}m gap..',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_linealt:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_linealt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_line:400:650}', 'y': '{randy_line:400:650}', 'z': '{randz_linealt:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_line2:400:650}', 'y': '{randy_line2:400:650}', 'z': '{randz_linealt:15:20}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_line:400:650}', 'y': '{randy_line:400:650}', 'z': '{randz_linealt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_line2:400:650}', 'y': '{randy_line2:400:650}', 'z': '{randz_linealt:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/two_drones_distance',
                        'parameters': {'drone_1_id': '{drone_1_id}', 'drone_2_id': '{drone_2_id}', 'max_distance': '{random_spacing:15:25}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover']
        },

        'formation_triangle': {
            'name': 'Triangle Formation - 3 Drones',
            'description': 'Three drones form a triangle formation around a target',
            'content': 'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} should take off to {random_formalt:18:24} meters altitude and form a triangle formation around target at position ({random_targetx:400:650}, {random_targety:400:650}, {random_formalt:18:24}). {drone_1_name} positions at ({random_targetx:400:650}, {random_targetnorthy:350:600}, {random_formalt:18:24}), {drone_2_name} at ({random_targetsouthwestx:350:600}, {random_targetswy:400:650}, {random_formalt:18:24}), and {drone_3_name} at ({random_targetsoutheastx:350:600}, {random_targetsey:400:650}, {random_formalt:18:24}). After formation is established, all drones maintain hovering.',
            'content_aliases': [
                'Have {drone_1_name}, {drone_2_name}, {drone_3_name} take off to {random_formalt:18:24}m, form a triangle around target ({random_targetx:400:650}, {random_targety:400:650}, {random_formalt:18:24}), with {drone_1_name} at ({random_targetx:400:650},{random_targetnorthy:350:600},{random_formalt:18:24}), {drone_2_name} at ({random_targetsouthwestx:350:600},{random_targetswy:400:650},{random_formalt:18:24}), and {drone_3_name} at ({random_targetsoutheastx:350:600},{random_targetsey:400:650},{random_formalt:18:24}), then hover.',
                'Triangle formation at {random_formalt:18:24}m around target ({random_targetx:400:650}, {random_targety:400:650}, {random_formalt:18:24}): {drone_1_name} holds ({random_targetx:400:650},{random_targetnorthy:350:600},{random_formalt:18:24}), {drone_2_name} holds ({random_targetsouthwestx:350:600},{random_targetswy:400:650},{random_formalt:18:24}), {drone_3_name} holds ({random_targetsoutheastx:350:600},{random_targetsey:400:650},{random_formalt:18:24}), all hovering.',
                'Three-drone triangulation: take off to {random_formalt:18:24}m, form a triangle around ({random_targetx:400:650}, {random_targety:400:650}, {random_formalt:18:24}) with positions {drone_1_name} ({random_targetx:400:650},{random_targetnorthy:350:600},{random_formalt:18:24}), {drone_2_name} ({random_targetsouthwestx:350:600},{random_targetswy:400:650},{random_formalt:18:24}), {drone_3_name} ({random_targetsoutheastx:350:600},{random_targetsey:400:650},{random_formalt:18:24}), then hover.',
                'Form a three-point hover after takeoff to {random_formalt:18:24}m around target ({random_targetx:400:650}, {random_targety:400:650}, {random_formalt:18:24}): {drone_1_name} at ({random_targetx:400:650},{random_targetnorthy:350:600},{random_formalt:18:24}), {drone_2_name} at ({random_targetsouthwestx:350:600},{random_targetswy:400:650},{random_formalt:18:24}), {drone_3_name} at ({random_targetsoutheastx:350:600},{random_targetsey:400:650},{random_formalt:18:24}), then hover.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{random_targetx:400:650}', 'y': '{random_targetnorthy:350:600}', 'z': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{random_targetsouthwestx:350:600}', 'y': '{random_targetswy:400:650}', 'z': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{random_targetsoutheastx:350:600}', 'y': '{random_targetsey:400:650}', 'z': '{random_formalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_3_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{random_targetx:400:650}', 'y': '{random_targetnorthy:350:600}', 'z': '{random_formalt:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{random_targetsouthwestx:350:600}', 'y': '{random_targetswy:400:650}', 'z': '{random_formalt:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_3_id}', 'x': '{random_targetsoutheastx:350:600}', 'y': '{random_targetsey:400:650}', 'z': '{random_formalt:18:24}', 'tolerance': 3.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover']
        },

        'multi_target_survey': {
            'name': 'Multi-Target Survey Mission',
            'description': 'Two drones survey two different targets',
            'content': 'Survey mission: Drone {drone_1_name} surveys target {target_1_name} while drone {drone_2_name} surveys target {target_2_name}. Both drones take off to {random_surveyalt:18:24} meters, fly to their respective targets, hover and capture photos.',
            'content_aliases': [
                'Have {drone_1_name} and {drone_2_name} take off to {random_surveyalt:18:24}m; {drone_1_name} surveys {target_1_name} and {drone_2_name} surveys {target_2_name}, each hovering to take photos.',
                'Parallel survey at {random_surveyalt:18:24}m: {drone_1_name} goes to {target_1_name} and {drone_2_name} goes to {target_2_name}, with hover and photo capture at each target.',
                'Split reconnaissance at {random_surveyalt:18:24}m: {drone_1_name} heads to {target_1_name} and hovers for photos while {drone_2_name} heads to {target_2_name} and does the same.',
                'Dual-target documentation: ascend to {random_surveyalt:18:24}m, send {drone_1_name} to {target_1_name} and {drone_2_name} to {target_2_name}, hover and photograph both.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_surveyalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_surveyalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'hover', 'take_photo']
        },

        'perimeter_search': {
            'name': 'Perimeter Search - 4 Drones',
            'description': 'Four drones stationed at guard points for perimeter security',
            'content': 'Deploy drones {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} for perimeter search. All take off to {randz_perimalt:20:28} meters altitude. Position {drone_1_name} at guard point ({randx_gard1:400:650},{randy_gard1:650:900},{randz_perimalt:20:28}), {drone_2_name} at guard point ({randx_gard2:650:900},{randy_gard2:400:650},{randz_perimalt:20:28}), {drone_3_name} at guard point ({randx_gard3:400:650},{randy_gard3:150:400},{randz_perimalt:20:28}), and {drone_4_name} at west guard point ({randx_gard4:150:400},{randy_gard4:400:650},{randz_perimalt:20:28}). All drones hover, take photos at their positions, and maintain search.',
            'content_aliases': [
                'Launch {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name} to {randz_perimalt:20:28}m and assign guard points: {drone_1_name} ({randx_gard1:400:650},{randy_gard1:650:900},{randz_perimalt:20:28}), {drone_2_name} ({randx_gard2:650:900},{randy_gard2:400:650},{randz_perimalt:20:28}), {drone_3_name} ({randx_gard3:400:650},{randy_gard3:150:400},{randz_perimalt:20:28}), {drone_4_name} ({randx_gard4:150:400},{randy_gard4:400:650},{randz_perimalt:20:28}); hover and take photos.',
                'Perimeter watch at {randz_perimalt:20:28}m: {drone_1_name} holds ({randx_gard1:400:650},{randy_gard1:650:900},{randz_perimalt:20:28}), {drone_2_name} holds ({randx_gard2:650:900},{randy_gard2:400:650},{randz_perimalt:20:28}), {drone_3_name} holds ({randx_gard3:400:650},{randy_gard3:150:400},{randz_perimalt:20:28}), {drone_4_name} holds ({randx_gard4:150:400},{randy_gard4:400:650},{randz_perimalt:20:28}); each hovers and captures imagery.',
                'Deploy a four-drone perimeter screen: send {drone_1_name} to ({randx_gard1:400:650},{randy_gard1:650:900},{randz_perimalt:20:28}), {drone_2_name} to ({randx_gard2:650:900},{randy_gard2:400:650},{randz_perimalt:20:28}), {drone_3_name} to ({randx_gard3:400:650},{randy_gard3:150:400},{randz_perimalt:20:28}), {drone_4_name} to ({randx_gard4:150:400},{randy_gard4:400:650},{randz_perimalt:20:28}) after takeoff to {randz_perimalt:20:28}m; hover and photograph.',
                'Form guard posts at {randz_perimalt:20:28}m with {drone_1_name} at ({randx_gard1:400:650},{randy_gard1:650:900},{randz_perimalt:20:28}), {drone_2_name} at ({randx_gard2:650:900},{randy_gard2:400:650},{randz_perimalt:20:28}), {drone_3_name} at ({randx_gard3:400:650},{randy_gard3:150:400},{randz_perimalt:20:28}), and {drone_4_name} at ({randx_gard4:150:400},{randy_gard4:400:650},{randz_perimalt:20:28}); maintain hover and take photos.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_gard1:400:650}', 'y': '{randy_gard1:650:900}', 'z': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_gard2:650:900}', 'y': '{randy_gard2:400:650}', 'z': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_gard3:400:650}', 'y': '{randy_gard3:150:400}', 'z': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_4_id}', 'x': '{randx_gard4:150:400}', 'y': '{randy_gard4:400:650}', 'z': '{randz_perimalt:20:28}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_3_id}'}},
                {'endpoint': '/drones/{id}/command/hover', 'parameters': {'id': '{drone_4_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_3_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_4_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_gard1:400:650}', 'y': '{randy_gard1:650:900}', 'z': '{randz_perimalt:20:28}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_gard2:650:900}', 'y': '{randy_gard2:400:650}', 'z': '{randz_perimalt:20:28}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_gard3:400:650}', 'y': '{randy_gard3:150:400}', 'z': '{randz_perimalt:20:28}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_4_id}', 'x': '{randx_gard4:150:400}', 'y': '{randy_gard4:400:650}', 'z': '{randz_perimalt:20:28}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_count': 1}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'hover', 'take_photo']
        },

        

        'dual_drone_same_target': {
            'name': 'Dual Drone Same Target',
            'description': 'Two drones fly to the same target together',
            'content': 'Send drones {drone_1_name} and {drone_2_name} to target {target_name}. Both drones should take off to {random_dualassignalt:14:20} meters and reach the same target.',
            'content_aliases': [
                'Launch {drone_1_name} and {drone_2_name} to {random_dualassignalt:14:20}m and have both fly to {target_name}.',
                'Coordinate {drone_1_name} and {drone_2_name} so they both reach target {target_name} after takeoff to {random_dualassignalt:14:20} meters.',
                'Two-drone convergence mission: {drone_1_name} and {drone_2_name} take off to {random_dualassignalt:14:20}m and head for {target_name}.',
                'Assign the same target to {drone_1_name} and {drone_2_name}; both should climb to {random_dualassignalt:14:20}m and reach {target_name}.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_dualassignalt:14:20}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_dualassignalt:14:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_dualassignalt:14:20}', 'max_altitude': '{random_dualassignalt:14:20}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_dualassignalt:14:20}', 'max_altitude': '{random_dualassignalt:14:20}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_reached_drone_number',
                        'parameters': {'target_id': '{target_id}', 'expected_count': 2}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_2_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },

        'relay_find_and_support_target': {
            'name': 'Relay Find and Support Target',
            'description': 'One drone finds a target and another follows to support',
            'content': 'Drone {drone_1_name} should first find and reach target {target_name}. After that, drone {drone_2_name} should fly to the same target as support. Both drones should operate at {random_relayalt:15:21} meters.',
            'content_aliases': [
                'Use {drone_1_name} to locate {target_name}, then send {drone_2_name} to the same target after both take off to {random_relayalt:15:21}m.',
                'Relay support mission: {drone_1_name} reaches {target_name} first, and {drone_2_name} follows to that target at {random_relayalt:15:21} meters.',
                'Have {drone_1_name} acquire target {target_name}, then dispatch {drone_2_name} to reinforce at the same location from {random_relayalt:15:21}m altitude.',
                'Two-stage target assignment: {drone_1_name} finds {target_name}, then {drone_2_name} joins at the same target after takeoff to {random_relayalt:15:21}m.',
            ],
            'difficulty': 'medium',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_relayalt:15:21}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_relayalt:15:21}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_relayalt:15:21}', 'max_altitude': '{random_relayalt:15:21}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_relayalt:15:21}', 'max_altitude': '{random_relayalt:15:21}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_2_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },

        'triple_drone_target_search': {
            'name': 'Triple Drone Target Search',
            'description': 'Three drones cooperatively search a single target',
            'content': 'Assign drones {drone_1_name}, {drone_2_name}, and {drone_3_name} to search target {target_name}. All three drones should take off to {randz_triplesearch:18:24} meters, converge on the target, and complete the search together.',
            'content_aliases': [
                'Have {drone_1_name}, {drone_2_name}, and {drone_3_name} take off to {randz_triplesearch:18:24}m and cooperatively search {target_name}.',
                'Three-drone target search: launch {drone_1_name}, {drone_2_name}, and {drone_3_name} to {randz_triplesearch:18:24}m and fully search {target_name}.',
                'Coordinate a shared search on {target_name} with {drone_1_name}, {drone_2_name}, and {drone_3_name} after takeoff to {randz_triplesearch:18:24} meters.',
                'Send {drone_1_name}, {drone_2_name}, and {drone_3_name} to {target_name}; all three should participate and complete the target search from {randz_triplesearch:18:24}m altitude.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_triplesearch:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_triplesearch:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_triplesearch:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{randz_triplesearch:18:24}', 'max_altitude': '{randz_triplesearch:18:24}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{randz_triplesearch:18:24}', 'max_altitude': '{randz_triplesearch:18:24}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_altitude': '{randz_triplesearch:18:24}', 'max_altitude': '{randz_triplesearch:18:24}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_reached_drone_number',
                        'parameters': {'target_id': '{target_id}', 'expected_count': 3}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_id}', 'drone_id': '{drone_3_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },


        'cross_target_swap_after_discovery': {
            'name': 'Cross Target Swap After Discovery',
            'description': 'Two drones reach separate targets, then swap targets',
            'content': 'Drone {drone_1_name} should find target {target_1_name}, and drone {drone_2_name} should find target {target_2_name}. After the first discovery, the drones swap assignments: {drone_1_name} goes to {target_2_name} and {drone_2_name} goes to {target_1_name} at {random_crossswapalt:16:22} meters.',
            'content_aliases': [
                'Send {drone_1_name} to {target_1_name} and {drone_2_name} to {target_2_name}, then have them exchange targets after takeoff to {random_crossswapalt:16:22}m.',
                'Cross-assignment mission: {drone_1_name} reaches {target_1_name}, {drone_2_name} reaches {target_2_name}, then both swap and fly to the opposite target at {random_crossswapalt:16:22} meters.',
                'Use {drone_1_name} and {drone_2_name} for a target swap at {random_crossswapalt:16:22}m: {drone_1_name} first finds {target_1_name}, {drone_2_name} first finds {target_2_name}, then they move to the opposite targets.',
                'Two drones, two targets, then swap at {random_crossswapalt:16:22}m: {drone_1_name} handles {target_1_name} first and later {target_2_name}, while {drone_2_name} handles {target_2_name} first and later {target_1_name}.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_crossswapalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_crossswapalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_crossswapalt:16:22}', 'max_altitude': '{random_crossswapalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_crossswapalt:16:22}', 'max_altitude': '{random_crossswapalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_2_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },

        'two_find_two_support': {
            'name': 'Two Find Two Support',
            'description': 'Two drones find two targets and two others support them',
            'content': 'Assign drone {drone_1_name} to target {target_1_name} and drone {drone_2_name} to target {target_2_name}. After those targets are found, send drone {drone_3_name} to {target_1_name} and drone {drone_4_name} to {target_2_name}. All four drones should operate at {random_supportalt:16:22} meters.',
            'content_aliases': [
                'Use {drone_1_name} and {drone_2_name} to find {target_1_name} and {target_2_name}, then dispatch {drone_3_name} and {drone_4_name} to those same targets at {random_supportalt:16:22}m.',
                'Two-find-two-support mission at {random_supportalt:16:22}m: {drone_1_name} reaches {target_1_name}, {drone_2_name} reaches {target_2_name}, then {drone_3_name} supports {target_1_name} and {drone_4_name} supports {target_2_name}.',
                'Launch four drones to {random_supportalt:16:22}m: first pair {drone_1_name}/{drone_2_name} finds {target_1_name}/{target_2_name}, second pair {drone_3_name}/{drone_4_name} reinforces those same targets.',
                'Stage a two-target reinforcement task at {random_supportalt:16:22}m where {drone_1_name} and {drone_2_name} make first contact, then {drone_3_name} joins at {target_1_name} and {drone_4_name} joins at {target_2_name}.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_supportalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_supportalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{random_supportalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{random_supportalt:16:22}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_4_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_altitude': '{random_supportalt:16:22}', 'max_altitude': '{random_supportalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_altitude': '{random_supportalt:16:22}', 'max_altitude': '{random_supportalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_altitude': '{random_supportalt:16:22}', 'max_altitude': '{random_supportalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_off',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_altitude': '{random_supportalt:16:22}', 'max_altitude': '{random_supportalt:16:22}', 'tolerance': 1.0}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_4_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },


        'target_assignment_progress_50_three_targets': {
            'name': 'Target Assignment 50% Progress With 3 Targets',
            'description': 'Reach three required targets and continue target assignment until progress exceeds 50%',
            'content': 'Take off necessary drones and assign them to reach required targets {target_1_name}, {target_2_name}, and {target_3_name}; if those targets alone do not exceed 50% session task progress, continue reaching additional assigned targets until progress exceeds 50%.',
            'content_aliases': [
                'Dispatch available drones to the mandatory targets {target_1_name}, {target_2_name}, and {target_3_name}, then reach more assigned targets as needed until progress passes 50%.',
                'Ensure {target_1_name}, {target_2_name}, and {target_3_name} are reached, and keep assigning drones to other targets if needed to push session progress above 50%.',
                'Use drones to cover required targets {target_1_name}, {target_2_name}, and {target_3_name}, then continue with additional assigned targets until session progress is over 50%.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['target_assignment'],
            'related_apis': [],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/task_progress',
                        'parameters': {'expected_progress': 0.5}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_3_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },


        'target_assignment_progress_70_five_targets': {
            'name': 'Target Assignment 70% Progress With 5 Targets',
            'description': 'Reach five required targets and continue target assignment until progress exceeds 70%',
            'content': 'Take off necessary drones and assign them to reach required targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, and {target_5_name}; if those targets alone do not exceed 70% session task progress, continue reaching additional assigned targets until progress exceeds 70%.',
            'content_aliases': [
                'Dispatch available drones to the mandatory targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, and {target_5_name}, then reach more assigned targets as needed until progress passes 70%.',
                'Ensure {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, and {target_5_name} are reached, and keep assigning drones to other targets if needed to push session progress above 70%.',
                'Use drones to cover required targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, and {target_5_name}, then continue with additional assigned targets until session progress is over 70%.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['target_assignment'],
            'related_apis': [],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/task_progress',
                        'parameters': {'expected_progress': 0.7}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_4_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached',
                        'parameters': {'target_id': '{target_5_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },


        'target_assignment': {
            'name': 'Target Assignment Task Completion',
            'description': 'Assign targets and reach 95% session task progress',
            'content': 'take off necessary drones and  assigned them to all targets (within task radius) until the session task progress exceeds 95%.',
            'content_aliases': [
                'Launch the required drones and assign them to all targets within the task radius until session progress passes 95%.',
                'Assign all targets to the available drones and continue until overall task progress exceeds 95%.',
                'Dispatch necessary drones to cover every target and keep working until session task progress is above 95%.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['target_assignment'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_id}', 'altitude': '{random_assignalt:12:18}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/task_progress',
                        'parameters': {'expected_progress': 0.95}
                    }
                ]
            },
            'commands': ['take_off', 'move_to']
        },


        'coordinated_search_sweep': {
            'name': 'Coordinated Search Sweep - 3 Drones',
            'description': 'Three drones perform coordinated parallel search sweep',
            'content': 'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} execute coordinated search sweep of target {target_name}, reaching 85%. All take off to {randz_sweep:20:25} meters. Drones maintain parallel formation {random_spacing:20:30:1} meters apart and sweep through the target area in synchronized pattern. Each drone takes photos during sweep.',
            'content_aliases': [
                'Have {drone_1_name}, {drone_2_name}, {drone_3_name} take off to {randz_sweep:20:25}m and sweep {target_name} with 85% area in parallel, keeping {random_spacing:20:30:1}m spacing and taking photos.',
                'Three-drone search line at {randz_sweep:20:25}m: {drone_1_name}, {drone_2_name}, {drone_3_name} maintain {random_spacing:20:30:1}m separation while sweeping across {target_name} with 85% area and capturing imagery.',
                'Coordinated sweep 85% area of {target_name}: {drone_1_name}, {drone_2_name}, {drone_3_name} fly a parallel pattern at {randz_sweep:20:25}m with {random_spacing:20:30:1}m intervals and take photos.',
                'Launch {drone_1_name}, {drone_2_name}, {drone_3_name} to {randz_sweep:20:25}m, hold {random_spacing:20:30:1}m spacing, and scan {target_name} in a synchronized 85% area sweep while each drone captures photos.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['area_search','area_assignment_and_patrol'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_sweep:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_sweep:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_sweep:20:25}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_3_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_searched_area_percentage',
                        'parameters': {'target_id': '{target_id}', 'expected_percentage': 0.85}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_count': 1}
                    },
                    {
                        'endpoint': '/check/drone_has_taken_photo',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_count': 1}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_along_path', 'take_photo']
        },

        

        'multiple_target_inspection_advanced': {
            'name': 'Multiple Target Inspection - Advanced',
            'description': 'Three drones each find and photograph two targets',
            'content': 'Drones {drone_1_name}, {drone_2_name}, and {drone_3_name} must take off to {random_advancedalt:18:24} meters. {drone_1_name} photographs targets {target_1_name} and {target_2_name}. {drone_2_name} photographs targets {target_3_name} and {target_4_name}. {drone_3_name} photographs targets {target_5_name} and {target_6_name}.',
            'content_aliases': [
                'Have {drone_1_name}, {drone_2_name}, {drone_3_name} take off to {random_advancedalt:18:24}m; {drone_1_name} visits {target_1_name}/{target_2_name}, {drone_2_name} visits {target_3_name}/{target_4_name}, {drone_3_name} visits {target_5_name}/{target_6_name} for photos.',
                'Coordinated multi-drone inspection at {random_advancedalt:18:24}m: {drone_1_name} photographs {target_1_name}/{target_2_name}, {drone_2_name} photographs {target_3_name}/{target_4_name}, {drone_3_name} photographs {target_5_name}/{target_6_name}.',
                'Three-drone photo sweep: climb to {random_advancedalt:18:24} meters, then {drone_1_name} images {target_1_name} and {target_2_name}, {drone_2_name} images {target_3_name} and {target_4_name}, {drone_3_name} images {target_5_name} and {target_6_name}.',
                'Assign target pairs at {random_advancedalt:18:24}m: {drone_1_name} handles {target_1_name}/{target_2_name}, {drone_2_name} handles {target_3_name}/{target_4_name}, {drone_3_name} handles {target_5_name}/{target_6_name}.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{random_advancedalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{random_advancedalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{random_advancedalt:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_1_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_2_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_3_id}'}},
                {'endpoint': '/drones/{id}/command/take_photo', 'parameters': {'id': '{drone_3_id}'}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_3_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_3_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_4_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_4_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_5_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_5_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_6_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_in_photo_taken_by_drone',
                        'parameters': {'target_id': '{target_6_id}', 'drone_id': '{drone_3_id}'}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'take_photo', 'move_to', 'take_photo']
        },


        'fleet_coordination_takeoff_and_formation': {
            'name': 'Fleet Coordinated Takeoff and Formation (3 Drones)',
            'description': 'Three drones take off and hold formation - uses per-drone history checks',
            'content': 'Three-drone coordination exercise: {drone_1_name}, {drone_2_name}, and {drone_3_name} take off together to {randz_fleet:15:20} meters altitude, then hold formation at positions ({randx_fleet1:400:650}, {randy_fleet1:400:650}, {randz_fleet}), ({randx_fleet2:650:900}, {randy_fleet2:400:650}, {randz_fleet}), and ({randx_fleet3:400:650}, {randy_fleet3:650:900}, {randz_fleet}) respectively for synchronized operation. Then all three drones move north for {randint_north:50:100}m, and next move east for {randint_east:50:100}m. Each drone must complete the specified directional movements (north {randint_north:50:100}m, then east {randint_east:50:100}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, and {drone_3_name}: ascend together to {randz_fleet:15:20} meters, establish formation at positions ({randx_fleet1:400:650}, {randy_fleet1:400:650}, {randz_fleet}), ({randx_fleet2:650:900}, {randy_fleet2:400:650}, {randz_fleet}), and ({randx_fleet3:400:650}, {randy_fleet3:650:900}, {randz_fleet}) respectively, then execute coordinated movement north {randint_north:50:100}m followed by east {randint_east:50:100}m. All drones must complete the full directional distance (north {randint_north:50:100}m, east {randint_east:50:100}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Three-drone formation drill: launch {drone_1_name}, {drone_2_name}, and {drone_3_name} to altitude {randz_fleet:15:20}m, hold stations at ({randx_fleet1:400:650}, {randy_fleet1:400:650}, {randz_fleet}), ({randx_fleet2:650:900}, {randy_fleet2:400:650}, {randz_fleet}), and ({randx_fleet3:400:650}, {randy_fleet3:650:900}, {randz_fleet}) respectively, then shift north by {randint_north:50:100} meters and east by {randint_east:50:100} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute synchronized operation with {drone_1_name}, {drone_2_name}, {drone_3_name}: take off reaching {randz_fleet:15:20} meters height, maintain formation at coordinates ({randx_fleet1:400:650}, {randy_fleet1:400:650}, {randz_fleet}), ({randx_fleet2:650:900}, {randy_fleet2:400:650}, {randz_fleet}), and ({randx_fleet3:400:650}, {randy_fleet3:650:900}, {randz_fleet}) respectively, then proceed north for {randint_north:50:100}m and subsequently east for {randint_east:50:100}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Three-drone coordinated maneuver: {drone_1_name}, {drone_2_name}, and {drone_3_name} lift off to {randz_fleet:15:20}m elevation, hold formation positions at ({randx_fleet1:400:650}, {randy_fleet1:400:650}, {randz_fleet}), ({randx_fleet2:650:900}, {randy_fleet2:400:650}, {randz_fleet}), and ({randx_fleet3:400:650}, {randy_fleet3:650:900}, {randz_fleet}) respectively, then travel north {randint_north:50:100} meters and east {randint_east:50:100} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_fleet1:400:650}', 'y': '{randy_fleet1:400:650}', 'z': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_fleet2:650:900}', 'y': '{randy_fleet2:400:650}', 'z': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_fleet3:400:650}', 'y': '{randy_fleet3:650:900}', 'z': '{randz_fleet:15:20}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_north:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_north:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_north:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_east:50:100}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_east:50:100}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_east:50:100}', 'heading': 90}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_1_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_2_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_3_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_fleet1:400:650}', 'y': '{randy_fleet1:400:650}', 'z': '{randz_fleet:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_fleet2:650:900}', 'y': '{randy_fleet2:400:650}', 'z': '{randz_fleet:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_fleet3:400:650}', 'y': '{randy_fleet3:650:900}', 'z': '{randz_fleet:15:20}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_north:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_north:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_north:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_east:50:100}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_east:50:100}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_east:50:100}', 'heading': 90, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },



        'fleet_coordination_takeoff_and_formation_4drones': {
            'name': 'Fleet Coordinated Takeoff and Formation (4 Drones)',
            'description': 'Four drones take off and hold a square formation - per-drone history checks',
            'content': 'Four-drone coordination exercise: {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} take off together to {randz_fleet4:18:24} meters altitude, then hold formation at positions ({randx_fleet4-1:360:520}, {randy_fleet4-1:360:520}, {randz_fleet4}), ({randx_fleet4-2:520:680}, {randy_fleet4-2:360:520}, {randz_fleet4}), ({randx_fleet4-3:520:680}, {randy_fleet4-3:520:680}, {randz_fleet4}), and ({randx_fleet4-4:360:520}, {randy_fleet4-4:520:680}, {randz_fleet4}) respectively for synchronized operation. Then all four drones move north for {randint_north4:60:120}m, and next move east for {randint_east4:60:120}m. Each drone must complete the specified directional movements (north {randint_north4:60:120}m, then east {randint_east4:60:120}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name}: ascend together to {randz_fleet4:18:24} meters, establish square formation at positions ({randx_fleet4-1:360:520}, {randy_fleet4-1:360:520}, {randz_fleet4}), ({randx_fleet4-2:520:680}, {randy_fleet4-2:360:520}, {randz_fleet4}), ({randx_fleet4-3:520:680}, {randy_fleet4-3:520:680}, {randz_fleet4}), and ({randx_fleet4-4:360:520}, {randy_fleet4-4:520:680}, {randz_fleet4}) respectively, then execute coordinated movement north {randint_north4:60:120}m followed by east {randint_east4:60:120}m. All drones must complete the full directional distance (north {randint_north4:60:120}m, east {randint_east4:60:120}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Four-drone formation drill: launch {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} to altitude {randz_fleet4:18:24}m, hold stations at ({randx_fleet4-1:360:520}, {randy_fleet4-1:360:520}, {randz_fleet4}), ({randx_fleet4-2:520:680}, {randy_fleet4-2:360:520}, {randz_fleet4}), ({randx_fleet4-3:520:680}, {randy_fleet4-3:520:680}, {randz_fleet4}), and ({randx_fleet4-4:360:520}, {randy_fleet4-4:520:680}, {randz_fleet4}) respectively, then shift north by {randint_north4:60:120} meters and east by {randint_east4:60:120} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute synchronized operation with {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}: take off reaching {randz_fleet4:18:24} meters height, maintain formation at coordinates ({randx_fleet4-1:360:520}, {randy_fleet4-1:360:520}, {randz_fleet4}), ({randx_fleet4-2:520:680}, {randy_fleet4-2:360:520}, {randz_fleet4}), ({randx_fleet4-3:520:680}, {randy_fleet4-3:520:680}, {randz_fleet4}), and ({randx_fleet4-4:360:520}, {randy_fleet4-4:520:680}, {randz_fleet4}) respectively, then proceed north for {randint_north4:60:120}m and subsequently east for {randint_east4:60:120}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Four-drone coordinated maneuver: {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} lift off to {randz_fleet4:18:24}m elevation, hold formation positions at ({randx_fleet4-1:360:520}, {randy_fleet4-1:360:520}, {randz_fleet4}), ({randx_fleet4-2:520:680}, {randy_fleet4-2:360:520}, {randz_fleet4}), ({randx_fleet4-3:520:680}, {randy_fleet4-3:520:680}, {randz_fleet4}), and ({randx_fleet4-4:360:520}, {randy_fleet4-4:520:680}, {randz_fleet4}) respectively, then travel north {randint_north4:60:120} meters and east {randint_east4:60:120} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_fleet4-1:360:520}', 'y': '{randy_fleet4-1:360:520}', 'z': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_fleet4-2:520:680}', 'y': '{randy_fleet4-2:360:520}', 'z': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_fleet4-3:520:680}', 'y': '{randy_fleet4-3:520:680}', 'z': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_4_id}', 'x': '{randx_fleet4-4:360:520}', 'y': '{randy_fleet4-4:520:680}', 'z': '{randz_fleet4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_north4:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_north4:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_north4:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_north4:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_east4:60:120}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_east4:60:120}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_east4:60:120}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_east4:60:120}', 'heading': 90}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_1_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_2_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_3_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_4_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_fleet4-1:360:520}', 'y': '{randy_fleet4-1:360:520}', 'z': '{randz_fleet4:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_fleet4-2:520:680}', 'y': '{randy_fleet4-2:360:520}', 'z': '{randz_fleet4:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_fleet4-3:520:680}', 'y': '{randy_fleet4-3:520:680}', 'z': '{randz_fleet4:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_4_id}', 'x': '{randx_fleet4-4:360:520}', 'y': '{randy_fleet4-4:520:680}', 'z': '{randz_fleet4:18:24}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_north4:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_north4:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_north4:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_north4:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_east4:60:120}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_east4:60:120}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_east4:60:120}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_east4:60:120}', 'heading': 90, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },

        'fleet_coordination_takeoff_and_formation_5drones': {
            'name': 'Fleet Coordinated Takeoff and Formation (5 Drones)',
            'description': 'Five drones take off and hold a pentagon formation - per-drone history checks',
            'content': 'Five-drone coordination exercise: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} take off together to {randz_fleet5:20:26} meters altitude, then hold formation at positions ({randx_fleet5-1:360:520}, {randy_fleet5-1:360:520}, {randz_fleet5}), ({randx_fleet5-2:520:680}, {randy_fleet5-2:320:480}, {randz_fleet5}), ({randx_fleet5-3:680:840}, {randy_fleet5-3:420:580}, {randz_fleet5}), ({randx_fleet5-4:560:720}, {randy_fleet5-4:560:720}, {randz_fleet5}), and ({randx_fleet5-5:380:540}, {randy_fleet5-5:540:700}, {randz_fleet5}) respectively for synchronized operation. Then all five drones move north for {randint_north5:70:130}m, and next move east for {randint_east5:70:130}m. Each drone must complete the specified directional movements (north {randint_north5:70:130}m, then east {randint_east5:70:130}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name}: ascend together to {randz_fleet5:20:26} meters, establish pentagon formation at positions ({randx_fleet5-1:360:520}, {randy_fleet5-1:360:520}, {randz_fleet5}), ({randx_fleet5-2:520:680}, {randy_fleet5-2:320:480}, {randz_fleet5}), ({randx_fleet5-3:680:840}, {randy_fleet5-3:420:580}, {randz_fleet5}), ({randx_fleet5-4:560:720}, {randy_fleet5-4:560:720}, {randz_fleet5}), and ({randx_fleet5-5:380:540}, {randy_fleet5-5:540:700}, {randz_fleet5}) respectively, then execute coordinated movement north {randint_north5:70:130}m followed by east {randint_east5:70:130}m. All drones must complete the full directional distance (north {randint_north5:70:130}m, east {randint_east5:70:130}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Five-drone formation drill: launch {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} to altitude {randz_fleet5:20:26}m, hold stations at ({randx_fleet5-1:360:520}, {randy_fleet5-1:360:520}, {randz_fleet5}), ({randx_fleet5-2:520:680}, {randy_fleet5-2:320:480}, {randz_fleet5}), ({randx_fleet5-3:680:840}, {randy_fleet5-3:420:580}, {randz_fleet5}), ({randx_fleet5-4:560:720}, {randy_fleet5-4:560:720}, {randz_fleet5}), and ({randx_fleet5-5:380:540}, {randy_fleet5-5:540:700}, {randz_fleet5}) respectively, then shift north by {randint_north5:70:130} meters and east by {randint_east5:70:130} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute synchronized operation with {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, {drone_5_name}: take off reaching {randz_fleet5:20:26} meters height, maintain formation at coordinates ({randx_fleet5-1:360:520}, {randy_fleet5-1:360:520}, {randz_fleet5}), ({randx_fleet5-2:520:680}, {randy_fleet5-2:320:480}, {randz_fleet5}), ({randx_fleet5-3:680:840}, {randy_fleet5-3:420:580}, {randz_fleet5}), ({randx_fleet5-4:560:720}, {randy_fleet5-4:560:720}, {randz_fleet5}), and ({randx_fleet5-5:380:540}, {randy_fleet5-5:540:700}, {randz_fleet5}) respectively, then proceed north for {randint_north5:70:130}m and subsequently east for {randint_east5:70:130}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Five-drone coordinated maneuver: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} lift off to {randz_fleet5:20:26}m elevation, hold formation positions at ({randx_fleet5-1:360:520}, {randy_fleet5-1:360:520}, {randz_fleet5}), ({randx_fleet5-2:520:680}, {randy_fleet5-2:320:480}, {randz_fleet5}), ({randx_fleet5-3:680:840}, {randy_fleet5-3:420:580}, {randz_fleet5}), ({randx_fleet5-4:560:720}, {randy_fleet5-4:560:720}, {randz_fleet5}), and ({randx_fleet5-5:380:540}, {randy_fleet5-5:540:700}, {randz_fleet5}) respectively, then travel north {randint_north5:70:130} meters and east {randint_east5:70:130} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_5_id}', 'altitude': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_1_id}', 'x': '{randx_fleet5-1:360:520}', 'y': '{randy_fleet5-1:360:520}', 'z': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_2_id}', 'x': '{randx_fleet5-2:520:680}', 'y': '{randy_fleet5-2:320:480}', 'z': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_3_id}', 'x': '{randx_fleet5-3:680:840}', 'y': '{randy_fleet5-3:420:580}', 'z': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_4_id}', 'x': '{randx_fleet5-4:560:720}', 'y': '{randy_fleet5-4:560:720}', 'z': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_to', 'parameters': {'id': '{drone_5_id}', 'x': '{randx_fleet5-5:380:540}', 'y': '{randy_fleet5-5:540:700}', 'z': '{randz_fleet5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_north5:70:130}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_north5:70:130}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_north5:70:130}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_north5:70:130}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_5_id}', 'distance': '{randint_north5:70:130}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_east5:70:130}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_east5:70:130}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_east5:70:130}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_east5:70:130}', 'heading': 90}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_5_id}', 'distance': '{randint_east5:70:130}', 'heading': 90}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_1_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_2_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_3_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_4_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_hovering',
                        'parameters': {'drone_id': '{drone_5_id}', 'tolerance': 0.5}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_1_id}', 'x': '{randx_fleet5-1:360:520}', 'y': '{randy_fleet5-1:360:520}', 'z': '{randz_fleet5:20:26}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_2_id}', 'x': '{randx_fleet5-2:520:680}', 'y': '{randy_fleet5-2:320:480}', 'z': '{randz_fleet5:20:26}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_3_id}', 'x': '{randx_fleet5-3:680:840}', 'y': '{randy_fleet5-3:420:580}', 'z': '{randz_fleet5:20:26}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_4_id}', 'x': '{randx_fleet5-4:560:720}', 'y': '{randy_fleet5-4:560:720}', 'z': '{randz_fleet5:20:26}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_visited_position',
                        'parameters': {'drone_id': '{drone_5_id}', 'x': '{randx_fleet5-5:380:540}', 'y': '{randy_fleet5-5:540:700}', 'z': '{randz_fleet5:20:26}', 'tolerance': 3.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_north5:70:130}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_north5:70:130}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_north5:70:130}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_north5:70:130}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_5_id}', 'min_distance': '{randint_north5:70:130}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_east5:70:130}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_east5:70:130}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_east5:70:130}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_east5:70:130}', 'heading': 90, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_5_id}', 'min_distance': '{randint_east5:70:130}', 'heading': 90, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },


        'fleet_coordination_target_sweep': {
            'name': 'Fleet Target Sweep (3 Drones)',
            'description': 'Three drones visit targets, then sweep west, south, and north',
            'content': 'Three-drone target sweep: {drone_1_name}, {drone_2_name}, and {drone_3_name} take off together to {randz_targetsweep:16:22} meters altitude. {drone_1_name} flies to target {target_1_name}, {drone_2_name} flies to target {target_2_name}, and {drone_3_name} flies to target {target_3_name}. After reaching the targets, all three drones move west for {randint_westsweep:40:90}m, then south for {randint_southsweep:40:90}m, then north for {randint_northsweep:40:90}m together. Each drone must complete the specified directional movements (west {randint_westsweep:40:90}m, south {randint_southsweep:40:90}m, north {randint_northsweep:40:90}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, and {drone_3_name}: ascend together to {randz_targetsweep:16:22} meters altitude, send {drone_1_name} to target {target_1_name}, {drone_2_name} to target {target_2_name}, and {drone_3_name} to target {target_3_name}, then execute coordinated sweep movement west {randint_westsweep:40:90}m, south {randint_southsweep:40:90}m, and north {randint_northsweep:40:90}m. All drones must complete the full directional distance (west {randint_westsweep:40:90}m, south {randint_southsweep:40:90}m, north {randint_northsweep:40:90}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Three-drone target sweep operation: launch {drone_1_name}, {drone_2_name}, and {drone_3_name} to altitude {randz_targetsweep:16:22}m, navigate to targets {target_1_name}, {target_2_name}, {target_3_name} respectively, then shift west by {randint_westsweep:40:90} meters, south by {randint_southsweep:40:90} meters, and north by {randint_northsweep:40:90} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute three-drone sweep mission: {drone_1_name}, {drone_2_name}, {drone_3_name} take off reaching {randz_targetsweep:16:22} meters height, fly to targets {target_1_name}, {target_2_name}, {target_3_name} respectively, then proceed west for {randint_westsweep:40:90}m, subsequently south for {randint_southsweep:40:90}m, and finally north for {randint_northsweep:40:90}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Three-drone coordinated target mission: {drone_1_name}, {drone_2_name}, and {drone_3_name} lift off to {randz_targetsweep:16:22}m elevation, reach targets {target_1_name}, {target_2_name}, {target_3_name} respectively, then travel west {randint_westsweep:40:90} meters, south {randint_southsweep:40:90} meters, and north {randint_northsweep:40:90} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_targetsweep:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_targetsweep:16:22}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_targetsweep:16:22}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_westsweep:40:90}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_westsweep:40:90}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_westsweep:40:90}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_southsweep:40:90}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_southsweep:40:90}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_southsweep:40:90}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_northsweep:40:90}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_northsweep:40:90}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_northsweep:40:90}', 'heading': 0}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_3_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_westsweep:40:90}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_westsweep:40:90}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_westsweep:40:90}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_southsweep:40:90}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_southsweep:40:90}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_southsweep:40:90}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_northsweep:40:90}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_northsweep:40:90}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_northsweep:40:90}', 'heading': 0, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },

        'fleet_coordination_target_sweep_4drones': {
            'name': 'Fleet Target Sweep (4 Drones)',
            'description': 'Four drones visit targets, then sweep west, south, and north',
            'content': 'Four-drone target sweep: {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} take off together to {randz_targetsweep4:18:24} meters altitude. {drone_1_name} flies to target {target_1_name}, {drone_2_name} flies to target {target_2_name}, {drone_3_name} flies to target {target_3_name}, and {drone_4_name} flies to target {target_4_name}. After reaching the targets, all four drones move west for {randint_westsweep4:50:100}m, then south for {randint_southsweep4:50:100}m, then north for {randint_northsweep4:50:100}m together. Each drone must complete the specified directional movements (west {randint_westsweep4:50:100}m, south {randint_southsweep4:50:100}m, north {randint_northsweep4:50:100}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name}: ascend together to {randz_targetsweep4:18:24} meters altitude, send {drone_1_name} to target {target_1_name}, {drone_2_name} to target {target_2_name}, {drone_3_name} to target {target_3_name}, and {drone_4_name} to target {target_4_name}, then execute coordinated sweep movement west {randint_westsweep4:50:100}m, south {randint_southsweep4:50:100}m, and north {randint_northsweep4:50:100}m. All drones must complete the full directional distance (west {randint_westsweep4:50:100}m, south {randint_southsweep4:50:100}m, north {randint_northsweep4:50:100}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Four-drone target sweep operation: launch {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} to altitude {randz_targetsweep4:18:24}m, navigate to targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name} respectively, then shift west by {randint_westsweep4:50:100} meters, south by {randint_southsweep4:50:100} meters, and north by {randint_northsweep4:50:100} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute four-drone sweep mission: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name} take off reaching {randz_targetsweep4:18:24} meters height, fly to targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name} respectively, then proceed west for {randint_westsweep4:50:100}m, subsequently south for {randint_southsweep4:50:100}m, and finally north for {randint_northsweep4:50:100}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Four-drone coordinated target mission: {drone_1_name}, {drone_2_name}, {drone_3_name}, and {drone_4_name} lift off to {randz_targetsweep4:18:24}m elevation, reach targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name} respectively, then travel west {randint_westsweep4:50:100} meters, south {randint_southsweep4:50:100} meters, and north {randint_northsweep4:50:100} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_targetsweep4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_targetsweep4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_targetsweep4:18:24}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{randz_targetsweep4:18:24}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_westsweep4:50:100}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_westsweep4:50:100}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_westsweep4:50:100}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_westsweep4:50:100}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_southsweep4:50:100}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_southsweep4:50:100}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_southsweep4:50:100}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_southsweep4:50:100}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_northsweep4:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_northsweep4:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_northsweep4:50:100}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_northsweep4:50:100}', 'heading': 0}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_3_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_4_id}', 'drone_id': '{drone_4_id}'}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_westsweep4:50:100}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_westsweep4:50:100}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_westsweep4:50:100}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_westsweep4:50:100}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_southsweep4:50:100}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_southsweep4:50:100}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_southsweep4:50:100}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_southsweep4:50:100}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_northsweep4:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_northsweep4:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_northsweep4:50:100}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_northsweep4:50:100}', 'heading': 0, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },

        'fleet_coordination_target_sweep_5drones': {
            'name': 'Fleet Target Sweep (5 Drones)',
            'description': 'Five drones visit targets, then sweep west, south, and north',
            'content': 'Five-drone target sweep: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} take off together to {randz_targetsweep5:20:26} meters altitude. {drone_1_name} flies to target {target_1_name}, {drone_2_name} flies to target {target_2_name}, {drone_3_name} flies to target {target_3_name}, {drone_4_name} flies to target {target_4_name}, and {drone_5_name} flies to target {target_5_name}. After reaching the targets, all five drones move west for {randint_westsweep5:60:120}m, then south for {randint_southsweep5:60:120}m, then north for {randint_northsweep5:60:120}m together. Each drone must complete the specified directional movements (west {randint_westsweep5:60:120}m, south {randint_southsweep5:60:120}m, north {randint_northsweep5:60:120}m) regardless of starting position - if obstacles block the path, drones should adjust position as needed to complete the full directed distance in each heading.',
            'content_aliases': [
                'Coordinate {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name}: ascend together to {randz_targetsweep5:20:26} meters altitude, send {drone_1_name} to target {target_1_name}, {drone_2_name} to target {target_2_name}, {drone_3_name} to target {target_3_name}, {drone_4_name} to target {target_4_name}, and {drone_5_name} to target {target_5_name}, then execute coordinated sweep movement west {randint_westsweep5:60:120}m, south {randint_southsweep5:60:120}m, and north {randint_northsweep5:60:120}m. All drones must complete the full directional distance (west {randint_westsweep5:60:120}m, south {randint_southsweep5:60:120}m, north {randint_northsweep5:60:120}m) from their respective positions, adjusting as needed to avoid obstacles.',
                'Five-drone target sweep operation: launch {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} to altitude {randz_targetsweep5:20:26}m, navigate to targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, {target_5_name} respectively, then shift west by {randint_westsweep5:60:120} meters, south by {randint_southsweep5:60:120} meters, and north by {randint_northsweep5:60:120} meters in synchronized operation. Each drone travels the specified distance in each direction regardless of obstacles encountered.',
                'Execute five-drone sweep mission: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, {drone_5_name} take off reaching {randz_targetsweep5:20:26} meters height, fly to targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, {target_5_name} respectively, then proceed west for {randint_westsweep5:60:120}m, subsequently south for {randint_southsweep5:60:120}m, and finally north for {randint_northsweep5:60:120}m together, with each drone completing the full directed movements by repositioning around obstacles if necessary.',
                'Five-drone coordinated target mission: {drone_1_name}, {drone_2_name}, {drone_3_name}, {drone_4_name}, and {drone_5_name} lift off to {randz_targetsweep5:20:26}m elevation, reach targets {target_1_name}, {target_2_name}, {target_3_name}, {target_4_name}, {target_5_name} respectively, then travel west {randint_westsweep5:60:120} meters, south {randint_southsweep5:60:120} meters, and north {randint_northsweep5:60:120} meters in sequence. The specified directional distances must be achieved by each drone, adapting position to circumvent any obstacles.',
            ],
            'difficulty': 'hard',
            'creator': 'Built-in template',
            'category': 'Multi-Drone Coordination',
            'is_builtin': True,
            'exclude_in_random_generation': False,
            'suitable_task': ['all'],
            'related_apis': [
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_1_id}', 'altitude': '{randz_targetsweep5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_2_id}', 'altitude': '{randz_targetsweep5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_3_id}', 'altitude': '{randz_targetsweep5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_4_id}', 'altitude': '{randz_targetsweep5:20:26}'}},
                {'endpoint': '/drones/{id}/command/take_off', 'parameters': {'id': '{drone_5_id}', 'altitude': '{randz_targetsweep5:20:26}'}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_westsweep5:60:120}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_westsweep5:60:120}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_westsweep5:60:120}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_westsweep5:60:120}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_5_id}', 'distance': '{randint_westsweep5:60:120}', 'heading': 270}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_southsweep5:60:120}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_southsweep5:60:120}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_southsweep5:60:120}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_southsweep5:60:120}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_5_id}', 'distance': '{randint_southsweep5:60:120}', 'heading': 180}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_1_id}', 'distance': '{randint_northsweep5:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_2_id}', 'distance': '{randint_northsweep5:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_3_id}', 'distance': '{randint_northsweep5:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_4_id}', 'distance': '{randint_northsweep5:60:120}', 'heading': 0}},
                {'endpoint': '/drones/{id}/command/move_towards', 'parameters': {'id': '{drone_5_id}', 'distance': '{randint_northsweep5:60:120}', 'heading': 0}}
            ],
            'execution_check_apis': {
                'logic': 'and',
                'checks': [
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_1_id}', 'drone_id': '{drone_1_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_2_id}', 'drone_id': '{drone_2_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_3_id}', 'drone_id': '{drone_3_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_4_id}', 'drone_id': '{drone_4_id}'}
                    },
                    {
                        'endpoint': '/check/target_is_reached_by_drone',
                        'parameters': {'target_id': '{target_5_id}', 'drone_id': '{drone_5_id}'}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_westsweep5:60:120}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_westsweep5:60:120}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_westsweep5:60:120}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_westsweep5:60:120}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_5_id}', 'min_distance': '{randint_westsweep5:60:120}', 'heading': 270, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_southsweep5:60:120}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_southsweep5:60:120}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_southsweep5:60:120}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_southsweep5:60:120}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_5_id}', 'min_distance': '{randint_southsweep5:60:120}', 'heading': 180, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_1_id}', 'min_distance': '{randint_northsweep5:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_2_id}', 'min_distance': '{randint_northsweep5:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_3_id}', 'min_distance': '{randint_northsweep5:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_4_id}', 'min_distance': '{randint_northsweep5:60:120}', 'heading': 0, 'tolerance': 5.0}
                    },
                    {
                        'endpoint': '/check/drone_has_moved_directed_distance',
                        'parameters': {'drone_id': '{drone_5_id}', 'min_distance': '{randint_northsweep5:60:120}', 'heading': 0, 'tolerance': 5.0}
                    }
                ]
            },
            'commands': ['take_off', 'move_to', 'move_towards']
        },

        
}
