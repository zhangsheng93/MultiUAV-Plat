# API Agent Guide

This guide is for developers building LLM-driven agents against the MultiUAV-Plat drone server, and for AI agents that need to operate the server safely and correctly.

It is not a full REST reference. For endpoint-by-endpoint details, see [API_REFERENCE.md](./API_REFERENCE.md), [API_DOCUMENTATION.md](./API_DOCUMENTATION.md), and [AUTHENTICATION.md](./AUTHENTICATION.md).

## 1. Scope

This document focuses on the default runtime contract for an autonomous agent:

- The agent authenticates with the `AGENT` API key.
- The agent uses only endpoints available to the `AGENT` role.
- The agent completes tasks by observing the current session, controlling drones, checking task status, and marking tasks done.

This is the intended baseline for production-like agent behavior. `SYSTEM` and `ADMIN` roles exist for platform tooling, scenario authoring, grading, and maintenance, but they are not the default operating mode for a task-solving agent.

## 2. Mental Model

An agent interacts with five core concepts:

- `Session`: the active mission world, including drones, tasks, and mission metadata.
- `Task`: a unit of work the agent is expected to complete.
- `Drone`: the controllable actor that executes commands.
- `Perception`: local information visible from a drone, such as nearby drones, targets, and obstacles.
- `Validation`: the mechanism used to determine whether a task has been satisfied.

The most important operational fact is that the server always has a notion of the **current active session**. Default agents should work against the current session, not assume they can create, restore, or globally inspect arbitrary sessions.

## 3. Authentication and Role Contract

The API uses the `X-API-Key` header.

Example:

```bash
curl -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/sessions/current/tasks
```

### Default agent rule

For the purposes of this guide, a runtime task-solving agent:

- uses the `AGENT` key,
- assumes only `AGENT` permissions,
- does not depend on `SYSTEM` or `ADMIN` endpoints,
- does not assume hidden validation details are visible.

### Role hierarchy

The implementation defines:

- `ADMIN > SYSTEM > USER > AGENT`

Important implementation detail from the server:

- If no API key is provided, the code currently defaults to the `AGENT` role.

Even so, a real agent integration should send the `AGENT` key explicitly rather than relying on omitted-key behavior.

## 4. What an AGENT Can and Cannot See

An `AGENT` can:

- list drones,
- inspect a specific drone,
- send drone commands,
- read the current session metadata,
- read current-session tasks,
- get the next pending task,
- run the current-session task check endpoint,
- mark current-session tasks done or pending,
- read local perception around a drone,
- read the current environment,
- inspect command history and command status.

An `AGENT` should not assume it can:

- create, delete, or edit drones,
- create, edit, or delete sessions,
- create, edit, or delete tasks,
- call raw `/check/*` grading endpoints,
- list global targets or obstacles,
- inspect full hidden task validation trees.

This restriction is deliberate. It forces the agent to behave like an operator inside the scenario rather than a privileged scenario author.

## 5. Hidden Fields and Task Masking

Tasks contain fields such as:

- `related_apis`
- `commands`
- `execution_check_apis`

For `AGENT` and `USER` roles, the server masks these fields:

- `related_apis` becomes an empty list,
- `commands` becomes an empty list,
- `execution_check_apis` becomes `null`.

This means an `AGENT` must solve tasks primarily from:

- `name`
- `content`
- `content_aliases`
- `description`
- `difficulty`
- `is_done`
- `is_passed`

Do not build a default agent that depends on hidden check definitions or privileged hints. If a task is only solvable when the hidden fields are visible, the task authoring is too brittle for AGENT-mode use.

## 6. The Standard Agent Loop

The recommended control loop is:

1. Get the current session.
2. Get the next pending task.
3. Inspect drones and choose one or more candidate drones.
4. Gather local context using drone state and nearby perception endpoints.
5. Execute a small number of commands.
6. Re-check the task.
7. If the task is satisfied, mark it done.
8. Repeat until no pending task remains.

This is intentionally short-horizon. A robust agent should prefer frequent observation and verification over long speculative command chains.

## 7. AGENT-Safe Endpoint Set

The following endpoints are the core working set for a default agent.

### Session

- `GET /sessions/current`
- `GET /sessions/current/tasks`
- `GET /sessions/current/tasks/next`
- `GET /sessions/current/tasks/{task_id}`
- `GET /sessions/current/tasks/{task_id}/check`
- `POST /sessions/current/tasks/{task_id}/mark-done`
- `POST /sessions/current/tasks/{task_id}/mark-pending`
- `GET /sessions/current/task-progress`

### Drones

- `GET /drones`
- `GET /drones/{id}`
- `GET /drones/{id}/commands`
- `GET /commands/{command_id}`

### Drone perception

- `GET /drones/{id}/nearby`
- `GET /drones/{id}/nearby/drones`
- `GET /drones/{id}/nearby/targets`
- `GET /drones/{id}/nearby/obstacles`

### Drone control

- `POST /drones/{id}/command`
- `POST /drones/{id}/command/take_off`
- `POST /drones/{id}/command/land`
- `POST /drones/{id}/command/move_to`
- `POST /drones/{id}/command/move_towards`
- `POST /drones/{id}/command/move_along_path`
- `POST /drones/{id}/command/change_altitude`
- `POST /drones/{id}/command/hover`
- `POST /drones/{id}/command/rotate`
- `POST /drones/{id}/command/return_home`
- `POST /drones/{id}/command/set_home`
- `POST /drones/{id}/command/calibrate`
- `POST /drones/{id}/command/take_photo`
- `POST /drones/{id}/command/send_message`
- `POST /drones/{id}/command/broadcast`
- `POST /drones/{id}/command/charge`

Command responses use semantic `status` values. `success` means the requested command completed fully. For `move_along_path`, `partial_success` means `allow_partial_move=true` let the drone reach at least one waypoint but stop before the final requested waypoint because an obstacle or insufficient battery blocked the remaining path. `error` means no allowed movement was executed for the failed command. Path responses include `successful_points_count`, `successful_points`, `unsuccessful_points_count`, and `unsuccessful_points`; point lists contain normalized `(x, y, z)` triples.

### Environment

- `GET /environments/current`

## 8. Current Session Usage

The default agent should anchor itself to the active session:

```bash
curl -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/sessions/current
```

The current session response provides:

- mission metadata,
- task type,
- task description,
- summary statistics,
- task count,
- aggregate task progress.

For `AGENT`, the current session should be treated as the authoritative mission context. Do not assume you can inspect all historical or hidden session internals.

## 9. Task Semantics

Each task includes at least:

- `id`
- `name`
- `content`
- `content_aliases`
- `description`
- `difficulty`
- `is_done`
- `is_passed`

### Important status fields

- `is_done`: operational completion flag
- `is_passed`: validation/pass flag

These are related but not identical.

Typical flow:

- The agent performs actions.
- The agent calls `GET /sessions/current/tasks/{task_id}/check`.
- If the check succeeds, the server sets `is_passed = true`.
- The agent then calls `POST /sessions/current/tasks/{task_id}/mark-done`.

An agent should not mark tasks done blindly. Prefer:

1. execute,
2. check,
3. mark done only after a successful check or strong observable evidence.

### Next pending task

`GET /sessions/current/tasks/next` returns the first task whose `is_done` is `false`.

That means:

- task order matters,
- “next” is queue-like, not planner-generated,
- agents should not assume the most semantically urgent task is returned if the task list was authored in a different order.

## 10. Session-Level Progress

`GET /sessions/current/task-progress` returns mission-level progress derived from the session `task_type`.

The code supports progress models such as:

- `area_search`
- `area_assignment_and_patrol`
- `target_assignment`
- `target_tracking`
- `others`

An agent can use this endpoint as a coarse mission signal, but task execution should still be driven primarily by the task queue and task check endpoint.

## 11. Drone State Model

The drone object includes operational state such as:

- `id`
- `name`
- `status`
- `position`
- `heading`
- `speed`
- `battery_level`
- `max_speed`
- `max_altitude`
- `perceived_radius`
- `task_radius`
- `home_position`

These fields are important for agent planning:

- `position`: current location for navigation
- `status`: whether takeoff, landing, hover, or movement is appropriate
- `battery_level`: whether a task is safe to continue
- `perceived_radius`: how much local information is visible
- `task_radius`: how close the drone needs to get for many task-related checks
- `home_position`: safe fallback and return target

## 12. Drone Command Model

The server supports two command styles:

- generic: `POST /drones/{id}/command`
- direct: `POST /drones/{id}/command/{command_name}`

Both are valid. For LLM agents, direct endpoints are usually simpler because they reduce formatting ambiguity.

### Common command patterns

Take off:

```bash
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  "http://localhost:8000/drones/drone-1/command/take_off?altitude=20"
```

Move:

```bash
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  "http://localhost:8000/drones/drone-1/command/move_to?x=120&y=80&z=20"
```

Take photo:

```bash
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  "http://localhost:8000/drones/drone-1/command/take_photo"
```

Land:

```bash
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  "http://localhost:8000/drones/drone-1/command/land"
```

### Command strategy guidance

Prefer:

- small action batches,
- state re-checks between commands,
- explicit altitude control,
- explicit position targets,
- conservative battery-aware execution.

Avoid:

- long unverified command chains,
- assuming movement succeeded without re-reading the drone state,
- assuming hidden map knowledge that AGENT does not actually possess.

## 13. Perception-Driven Planning

An AGENT generally should not rely on privileged global lists of targets or obstacles. Instead, it should use local perception:

- `GET /drones/{id}/nearby`
- `GET /drones/{id}/nearby/targets`
- `GET /drones/{id}/nearby/obstacles`
- `GET /drones/{id}/nearby/drones`

This enables a more realistic agent loop:

- observe nearby entities,
- infer what matters for the current task,
- move cautiously,
- re-observe after movement.

### Practical planning rules

- If a task references a target name or landmark, first check whether it is already in perception.
- If not visible, move incrementally rather than assuming a direct global route.
- Re-check nearby obstacles before committing to a path through cluttered space.
- Use the drone’s `task_radius` and `perceived_radius` when deciding whether to approach, hover, search, or validate.

## 14. Validation and Completion

For a default AGENT, the authoritative validation endpoint is:

- `GET /sessions/current/tasks/{task_id}/check`

This endpoint evaluates the hidden task validation logic on the server side. If the task passes, the server updates `is_passed` to `true`.

### Why this matters

`AGENT` cannot access the raw `/check/*` endpoints used in task authoring and grading. That is intentional. A default agent should treat task checking as a server-owned contract, not a local reimplementation.

### Recommended completion flow

1. Read the task.
2. Perform the minimal actions needed.
3. Call the task check endpoint.
4. If the result is `true`, mark the task done.
5. If the result is `false`, inspect drone state and local context, then retry.

### Tasks without hidden checks

If a task has no `execution_check_apis`, the current-session task check endpoint treats it as passed. This means tasks can be authored as purely operational tasks when needed, but such tasks should still be written clearly.

## 15. Recommended LLM Agent Architecture

A good implementation usually has four internal phases:

- `Observe`: read current session, tasks, drones, and perception
- `Plan`: choose the next small action sequence
- `Act`: execute one or a few commands
- `Verify`: check task state and update completion

This can be implemented as a loop with a compact memory object:

```text
session_id
current_task_id
candidate_drone_ids
last_seen_drone_states
last_check_result
retry_count
```

### Design principles

- Prefer short-horizon plans over long scripts.
- Re-read server state after meaningful actions.
- Treat command responses as tentative until state confirms them.
- Treat `partial_success` as movement progress, not endpoint arrival.
- Use `successful_points` and `unsuccessful_points` to understand which requested path waypoints were reached.
- Make retries bounded.
- Fall back to safe states such as hover, return home, or land when the situation is unclear.

## 16. Multi-Drone Strategy

When multiple drones exist, the agent should choose a drone based on:

- current position relative to the task,
- battery level,
- status,
- whether another drone is already closer,
- whether the task appears parallelizable.

Recommended patterns:

- use one drone as the primary executor unless the task clearly benefits from coordination,
- avoid issuing conflicting commands to multiple drones without a reason,
- use `send_message` or `broadcast` only if your agent architecture explicitly models inter-drone coordination.

## 17. Error Handling

A robust agent should explicitly handle:

- `401 Unauthorized`: bad or missing key configuration
- `403 Forbidden`: agent tried to use a non-AGENT-safe endpoint
- `404 Not Found`: missing current session, task, drone, or command
- `400 Bad Request`: malformed command parameters or invalid state transitions

Typical recovery rules:

- If there is no current session, stop and report a configuration/runtime problem.
- If there is no pending task, stop gracefully.
- If a command fails, re-read the drone and current task before retrying.
- If repeated task checks fail, switch from execution to diagnosis mode and gather fresh context.

## 18. Example End-to-End Workflow

The following sequence is a good baseline:

1. `GET /sessions/current`
2. `GET /sessions/current/tasks/next`
3. `GET /drones`
4. `GET /drones/{id}`
5. `GET /drones/{id}/nearby`
6. one or more drone command calls
7. `GET /sessions/current/tasks/{task_id}/check`
8. `POST /sessions/current/tasks/{task_id}/mark-done`

Example shell flow:

```bash
# 1. Get next task
curl -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/sessions/current/tasks/next

# 2. Inspect drones
curl -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/drones

# 3. Move a drone
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  "http://localhost:8000/drones/drone-1/command/move_to?x=100&y=100&z=20"

# 4. Check completion
curl -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/sessions/current/tasks/task-1/check

# 5. Mark done if passed
curl -X POST \
  -H "X-API-Key: <AGENT_API_KEY>" \
  http://localhost:8000/sessions/current/tasks/task-1/mark-done
```

## 19. Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "<AGENT_API_KEY>"}

session_resp = requests.get(f"{BASE_URL}/sessions/current", headers=HEADERS)
session_resp.raise_for_status()
session_data = session_resp.json()

task_resp = requests.get(f"{BASE_URL}/sessions/current/tasks/next", headers=HEADERS)
task_resp.raise_for_status()
task = task_resp.json()

drones_resp = requests.get(f"{BASE_URL}/drones", headers=HEADERS)
drones_resp.raise_for_status()
drones = drones_resp.json()

if not drones:
    raise RuntimeError("No drones available")

drone_id = drones[0]["id"]

move_resp = requests.post(
    f"{BASE_URL}/drones/{drone_id}/command/move_to",
    headers=HEADERS,
    params={"x": 100, "y": 100, "z": 20},
)
move_resp.raise_for_status()

check_resp = requests.get(
    f"{BASE_URL}/sessions/current/tasks/{task['id']}/check",
    headers=HEADERS,
)
check_resp.raise_for_status()
check_data = check_resp.json()

if check_data.get("result"):
    done_resp = requests.post(
        f"{BASE_URL}/sessions/current/tasks/{task['id']}/mark-done",
        headers=HEADERS,
    )
    done_resp.raise_for_status()
```

This example is intentionally simple. A production agent should:

- choose drones deliberately,
- read local context before moving,
- handle retries,
- validate state after commands,
- keep a bounded action budget per task.

## 20. Guidance for Task Authors

If you are designing tasks that AGENT-mode LLMs should be able to complete, follow these rules:

- Put the operational objective in `content`, not only in hidden check logic.
- Assume hidden fields are unavailable to the runtime agent.
- Make success observable from normal AGENT actions and server-side task checking.
- Avoid requiring privileged world knowledge that AGENT cannot obtain.
- Use clear target names, regions, or behaviors that can be grounded through perception and motion.

Good AGENT-compatible tasks are understandable from the visible task text and solvable through normal drone control and observation.

## 21. Guidance for SYSTEM and ADMIN Tooling

`SYSTEM` and `ADMIN` roles are useful for:

- creating sessions,
- authoring tasks,
- editing scenario entities,
- running grading checks,
- debugging agent failures,
- exporting or resetting scenarios.

Keep this separate from runtime agent behavior. The cleanest platform design is:

- `SYSTEM`/`ADMIN` prepare and evaluate the scenario,
- `AGENT` solves the scenario using only AGENT-safe capabilities.

## 22. Common Pitfalls

### Building an agent that expects hidden task fields

This fails because AGENT responses intentionally mask `related_apis`, `commands`, and `execution_check_apis`.

### Treating `/check/*` as part of the AGENT contract

Those endpoints are for higher-privilege grading and tooling, not for default AGENT execution.

### Assuming global map knowledge

AGENT should usually navigate from visible task text, drone state, and nearby perception rather than from privileged target/obstacle listings.

### Marking done before checking

This creates false completion and weakens agent reliability.

### Long command chains without observation

This increases the risk of drift, invalid assumptions, and avoidable failures.

## 23. Recommended Starter Prompt for an LLM Agent

The following prompt shape works well for an AGENT-only integration:

```text
You are an autonomous drone task agent. You may use only AGENT-role endpoints and the AGENT API key.
Work only against the current active session.
Your loop is: read current mission context, get the next pending task, inspect drones, gather nearby perception, take a small number of actions, check the task, and mark it done only when it passes.
Do not assume access to hidden validation logic, privileged global target lists, obstacle lists, or ADMIN/SYSTEM endpoints.
Prefer short-horizon, verifiable actions and re-read state after acting.
```

## 24. Cross-References

- [API_REFERENCE.md](./API_REFERENCE.md)
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
- [TASK_TEMPLATE_EDIT_GUIDE.md](./TASK_TEMPLATE_EDIT_GUIDE.md)

## 25. Summary

The safest and most correct way to build an LLM agent for this server is:

- authenticate as `AGENT`,
- operate only on the current session,
- solve tasks from visible task text and observable state,
- use local drone perception instead of privileged global knowledge,
- verify completion through the current-session task check endpoint,
- mark tasks done only after verification.

That is the core contract this server exposes to a default autonomous agent.
