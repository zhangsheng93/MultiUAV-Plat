import assert from 'node:assert/strict';
import test from 'node:test';
import {
  addDefaultEntity,
  buildSessionSavePayload,
  cloneEditorDraft,
  deleteSelectedEntity,
  duplicateSelectedEntity,
  formatMovingPathText,
  formatVerticesText,
  getSelectedEntity,
  moveSelectedEntity,
  parseMovingPathText,
  parseVerticesText,
  selectNextAtSamePosition,
  snapPositionToGrid,
  updateSelectedEntity
} from './editorState.ts';
import type { SessionData, ViewerState } from './types.ts';

function makeState(): ViewerState {
  return {
    server_time: 1,
    status: 'active',
    session: {
      id: 'session-1',
      name: 'Demo',
      task_type: 'others',
      canvas_width: 300,
      canvas_height: 200,
      is_distance_3d: false
    },
    drones: [
      {
        id: 'd1',
        name: 'Drone 1',
        model: 'M1',
        status: 'idle',
        position: { x: 10, y: 20, z: 5 },
        heading: 90,
        speed: 0,
        battery_level: 80,
        max_speed: 20,
        max_altitude: 120,
        battery_capacity: 1000
      }
    ],
    targets: [
      {
        id: 't1',
        name: 'Target 1',
        type: 'polygon',
        position: { x: 40, y: 50, z: 0 },
        radius: 8,
        vertices: [
          { x: 40, y: 50, z: 0 },
          { x: 52, y: 50, z: 0 },
          { x: 40, y: 62, z: 0 }
        ]
      }
    ],
    obstacles: [
      {
        id: 'o1',
        name: 'Obstacle 1',
        type: 'circle',
        position: { x: 70, y: 80, z: 0 },
        radius: 10,
        height: 30
      }
    ],
    paths: {},
    task_progress: {},
    environment: null
  };
}

test('cloneEditorDraft deep clones runtime state before editing', () => {
  const source = makeState();
  const draft = cloneEditorDraft(source);

  draft.drones[0].position.x = 99;

  assert.equal(source.drones[0].position.x, 10);
  assert.equal(draft.drones[0].position.x, 99);
});

test('updateSelectedEntity updates editable fields without dropping existing values', () => {
  const draft = cloneEditorDraft(makeState());

  updateSelectedEntity(draft, { kind: 'drone', id: 'd1' }, {
    name: 'Survey Drone',
    position: { x: 15, z: 25 },
    battery_level: 72
  });

  assert.equal(draft.drones[0].name, 'Survey Drone');
  assert.deepEqual(draft.drones[0].position, { x: 15, y: 20, z: 25 });
  assert.equal(draft.drones[0].battery_level, 72);
});

test('updateSelectedEntity updates full drone scalar fields from 2D editor', () => {
  const draft = cloneEditorDraft(makeState());

  updateSelectedEntity(draft, { kind: 'drone', id: 'd1' }, {
    model: 'Survey-X',
    heading: 135,
    battery_level: 64,
    status: 'ready',
    max_speed: 32,
    max_altitude: 240,
    battery_capacity: 4200,
    perceived_radius: 180,
    task_radius: 16
  });

  assert.equal(draft.drones[0].model, 'Survey-X');
  assert.equal(draft.drones[0].heading, 135);
  assert.equal(draft.drones[0].battery_level, 64);
  assert.equal(draft.drones[0].status, 'ready');
  assert.equal(draft.drones[0].max_speed, 32);
  assert.equal(draft.drones[0].max_altitude, 240);
  assert.equal(draft.drones[0].battery_capacity, 4200);
  assert.equal(draft.drones[0].perceived_radius, 180);
  assert.equal(draft.drones[0].task_radius, 16);
});

test('target type changes apply 2D field cleanup rules', () => {
  const draft = cloneEditorDraft(makeState());

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, {
    type: 'moving',
    description: 'patrol',
    radius: 18,
    moving_duration: 30,
    velocity: { x: 1, y: 2, z: 0 }
  });

  assert.equal(draft.targets[0].type, 'moving');
  assert.equal(draft.targets[0].description, 'patrol');
  assert.equal(draft.targets[0].radius, 18);
  assert.equal(draft.targets[0].moving_duration, 30);
  assert.deepEqual(draft.targets[0].velocity, { x: 1, y: 2, z: 0 });
  assert.equal(draft.targets[0].charge_amount, undefined);

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, { type: 'waypoint', charge_amount: 25 });

  assert.equal(draft.targets[0].type, 'waypoint');
  assert.equal(draft.targets[0].charge_amount, 25);

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, { type: 'polygon' });

  assert.equal(draft.targets[0].type, 'polygon');
  assert.equal(draft.targets[0].radius, undefined);
  assert.equal(draft.targets[0].velocity, undefined);
  assert.equal(draft.targets[0].moving_duration, undefined);
  assert.equal(draft.targets[0].charge_amount, undefined);

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, { type: 'fixed', radius: 12 });

  assert.equal(draft.targets[0].type, 'fixed');
  assert.equal(draft.targets[0].radius, 12);
  assert.equal(draft.targets[0].vertices, undefined);
});

test('obstacle type changes apply 2D field cleanup rules', () => {
  const draft = cloneEditorDraft(makeState());

  updateSelectedEntity(draft, { kind: 'obstacle', id: 'o1' }, {
    type: 'ellipse',
    description: 'wide obstacle',
    width: 20,
    length: 35,
    height: 12
  });

  assert.equal(draft.obstacles[0].type, 'ellipse');
  assert.equal(draft.obstacles[0].description, 'wide obstacle');
  assert.equal(draft.obstacles[0].width, 20);
  assert.equal(draft.obstacles[0].length, 35);
  assert.equal(draft.obstacles[0].height, 12);
  assert.equal(draft.obstacles[0].radius, undefined);

  updateSelectedEntity(draft, { kind: 'obstacle', id: 'o1' }, { type: 'circle', radius: 9 });

  assert.equal(draft.obstacles[0].type, 'circle');
  assert.equal(draft.obstacles[0].radius, 9);
  assert.equal(draft.obstacles[0].width, undefined);
  assert.equal(draft.obstacles[0].length, undefined);
  assert.equal(draft.obstacles[0].vertices, undefined);
});

test('polygon vertex text helpers mirror the 2D editor format', () => {
  const vertices = parseVerticesText('10, 20\n30 20\n30, 40 # comment\n10, 20');

  assert.deepEqual(vertices, [
    { x: 10, y: 20, z: 0 },
    { x: 30, y: 20, z: 0 },
    { x: 30, y: 40, z: 0 }
  ]);
  assert.equal(formatVerticesText(vertices), '10, 20\n30, 20\n30, 40');
  assert.throws(() => parseVerticesText('1, 2\n3, 4'), /at least 3/i);
  assert.throws(() => parseVerticesText('0, 0\n10, 10\n20, 20'), /non-zero area/i);
});

test('moving path text helpers accept 2D and 3D waypoint rows', () => {
  const path = parseMovingPathText('10, 20\n30, 40, 50', 12);

  assert.deepEqual(path, [
    { x: 10, y: 20, z: 12 },
    { x: 30, y: 40, z: 50 }
  ]);
  assert.equal(formatMovingPathText(path), '10, 20, 12\n30, 40, 50');
  assert.throws(() => parseMovingPathText('1, 2, 3, 4', 0), /2 or 3/);
});

test('polygon vertex patches recompute target and obstacle centers', () => {
  const draft = cloneEditorDraft(makeState());
  const vertices = [
    { x: 0, y: 0, z: 0 },
    { x: 30, y: 0, z: 0 },
    { x: 0, y: 30, z: 0 }
  ];

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, { type: 'polygon', vertices });
  updateSelectedEntity(draft, { kind: 'obstacle', id: 'o1' }, { type: 'polygon', vertices });

  assert.deepEqual(draft.targets[0].position, { x: 10, y: 10, z: 0 });
  assert.deepEqual(draft.obstacles[0].position, { x: 10, y: 10, z: 0 });
});

test('moving target mode patches clean incompatible movement fields', () => {
  const draft = cloneEditorDraft(makeState());

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, {
    type: 'moving',
    movement_mode: 'path',
    moving_duration: 45,
    moving_path: [
      { x: 10, y: 10, z: 5 },
      { x: 20, y: 25, z: 5 }
    ],
    velocity: { x: 4, y: 0, z: 0 }
  });

  assert.equal(draft.targets[0].movement_mode, 'path');
  assert.equal(draft.targets[0].velocity, undefined);
  assert.deepEqual(draft.targets[0].moving_path, [
    { x: 10, y: 10, z: 5 },
    { x: 20, y: 25, z: 5 }
  ]);

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, {
    movement_mode: 'velocity',
    velocity: { x: 1, y: 2, z: 0 }
  });

  assert.equal(draft.targets[0].movement_mode, 'velocity');
  assert.deepEqual(draft.targets[0].velocity, { x: 1, y: 2, z: 0 });
  assert.deepEqual(draft.targets[0].moving_path, undefined);

  updateSelectedEntity(draft, { kind: 'target', id: 't1' }, { movement_mode: 'stationary' });

  assert.equal(draft.targets[0].movement_mode, 'stationary');
  assert.equal(draft.targets[0].moving_duration, 0);
  assert.equal(draft.targets[0].velocity, undefined);
  assert.equal(draft.targets[0].moving_path, undefined);
});

test('snapPositionToGrid mirrors 2D grid rounding', () => {
  assert.deepEqual(snapPositionToGrid({ x: 12.4, y: 17.6, z: 8.2 }, 10), { x: 10, y: 20, z: 8.2 });
  assert.deepEqual(snapPositionToGrid({ x: 12.4, y: 17.6, z: 8.2 }, 0), { x: 12.4, y: 17.6, z: 8.2 });
});

test('selectNextAtSamePosition cycles overlapping entities explicitly', () => {
  const draft = cloneEditorDraft(makeState());
  draft.targets[0].position = { x: 70, y: 80, z: 0 };

  const next = selectNextAtSamePosition(draft, { kind: 'target', id: 't1' });
  const wrapped = selectNextAtSamePosition(draft, next);

  assert.deepEqual(next, { kind: 'obstacle', id: 'o1' });
  assert.deepEqual(wrapped, { kind: 'target', id: 't1' });
  assert.equal(selectNextAtSamePosition(draft, { kind: 'drone', id: 'd1' }), null);
});

test('moveSelectedEntity moves polygon absolute vertices by the same delta', () => {
  const draft = cloneEditorDraft(makeState());

  moveSelectedEntity(draft, { kind: 'target', id: 't1' }, { x: 100, y: 120, z: 0 });

  assert.deepEqual(draft.targets[0].position, { x: 100, y: 120, z: 0 });
  assert.deepEqual(draft.targets[0].vertices, [
    { x: 100, y: 120, z: 0 },
    { x: 112, y: 120, z: 0 },
    { x: 100, y: 132, z: 0 }
  ]);
});

test('duplicateSelectedEntity creates a selected copy with new id, name, and offset position', () => {
  const draft = cloneEditorDraft(makeState());

  const nextSelection = duplicateSelectedEntity(draft, { kind: 'obstacle', id: 'o1' });

  assert.equal(draft.obstacles.length, 2);
  assert.equal(nextSelection?.kind, 'obstacle');
  assert.notEqual(draft.obstacles[1].id, 'o1');
  assert.equal(draft.obstacles[1].name, 'Obstacle 1 Copy');
  assert.deepEqual(draft.obstacles[1].position, { x: 82, y: 92, z: 0 });
});

test('deleteSelectedEntity removes the entity and clears selection', () => {
  const draft = cloneEditorDraft(makeState());

  const nextSelection = deleteSelectedEntity(draft, { kind: 'target', id: 't1' });

  assert.equal(nextSelection, null);
  assert.equal(draft.targets.length, 0);
});

test('addDefaultEntity inserts useful defaults and selects the new entity', () => {
  const draft = cloneEditorDraft(makeState());

  const nextSelection = addDefaultEntity(draft, 'drone');

  assert.equal(nextSelection.kind, 'drone');
  assert.equal(draft.drones.length, 2);
  assert.match(draft.drones[1].id, /^drone-/);
  assert.equal(draft.drones[1].battery_level, 100);
});

test('getSelectedEntity resolves all selectable kinds from a draft', () => {
  const draft = cloneEditorDraft(makeState());

  assert.equal(getSelectedEntity(draft, { kind: 'drone', id: 'd1' })?.name, 'Drone 1');
  assert.equal(getSelectedEntity(draft, { kind: 'target', id: 't1' })?.name, 'Target 1');
  assert.equal(getSelectedEntity(draft, { kind: 'obstacle', id: 'o1' })?.name, 'Obstacle 1');
  assert.equal(getSelectedEntity(draft, null), null);
});

test('buildSessionSavePayload preserves session data while replacing edited entities', () => {
  const draft = cloneEditorDraft(makeState());
  draft.drones[0].name = 'Edited';
  const sessionData: SessionData = {
    id: 'session-1',
    name: 'Demo',
    description: 'keep',
    status: 'active',
    creator: 'system',
    task_type: 'others',
    task_description: '',
    is_distance_3d: false,
    canvas_width: 300,
    canvas_height: 200,
    created_at: 10,
    last_updated: 20,
    statistics: {},
    drones: [],
    targets: [],
    obstacles: [],
    environment: { name: 'env' },
    tasks: [{ id: 'task-1' }],
    history: { command_history: [{ id: 'cmd-1' }] }
  };

  const payload = buildSessionSavePayload(sessionData, draft);

  assert.equal(payload.description, 'keep');
  assert.deepEqual(payload.environment, { name: 'env' });
  assert.deepEqual(payload.tasks, [{ id: 'task-1' }]);
  assert.equal(payload.drones[0].name, 'Edited');
  assert.equal(payload.targets.length, 1);
  assert.equal(payload.obstacles.length, 1);
});
