# Task Template Editing Guide (Single Source)

This is the one-stop guide for creating, editing, and using task templates. It merges all placeholder and template documentation so other Markdown files can be removed safely.

## 1) What the Template System Does
- Generate tasks quickly from reusable templates (built-in or custom).
- Store templates locally at `./templates/task_templates.json`. Built-in templates are protected from deletion.
- Apply placeholder substitution across content, content aliases, and related API parameters.
- Support single-entity, multi-entity (indexed), array, and random placeholders with sticky/randomized behavior.

## 2) Using Templates in the GUI
1. Open the **Task Templates** browser (Tasks tab → “From Template”).
2. Select a template to view its description/content; double-click or press **Use Template**.
3. In **Customize Template**:
   - Set the task name (required).
   - Fill entity dropdowns for drones/targets/obstacles (or choose `[RANDOM]` or `[ORDERED]`).
   - Enter values for other placeholders; random placeholders need no input.
   - The creator defaults to the username in settings.
4. Click **Create Task** for one task or **Batch Create** to generate many (names are auto-numbered). Placeholder substitution is applied before tasks are created.

## 3) Template Structure (JSON fields)
```json
{
  "name": "Template Name",                // required
  "description": "Short summary",
  "content": "Main task text with {placeholders}",
  "content_aliases": ["Alt phrasing 1", "Alt phrasing 2"],
  "difficulty": "easy|medium|hard",
  "creator": "Creator Name",
  "category": "Category Name",
  "is_builtin": true|false,
  "related_apis": [
    {
      "method": "POST",
      "path": "/drones/{drone_1_id}/command/move_to",
      "parameters": {
        "id": "{drone_1_id}",
        "x": "{random_x}",
        "y": "{random_y}",
        "z": "{random_altitude}"
      }
    }
  ]
}
```
- Templates live in `~/.multiuav/templates/`; use the GUI editor or edit JSON directly.
- The system adds `created_at` and `last_modified` timestamps automatically.

## 4) Placeholder Reference (all supported)

### A) Single-Entity Identifiers
- Drones: `{drone_id}`, `{drone_name}`
- Targets: `{target_id}`, `{target_name}`
- Obstacles: `{obstacle_id}`, `{obstacle_name}`

### B) Multi-Entity Indexed Identifiers (sticky per index)
- Drones: `{drone_1_id}`…`{drone_5_id}`, `{drone_1_name}`…`{drone_5_name}`
- Targets: `{target_1_id}`…`{target_3_id}`, `{target_1_name}`…`{target_3_name}`
- Obstacles: `{obstacle_1_id}`…`{obstacle_3_id}`, `{obstacle_1_name}`…`{obstacle_3_name}`
- The UI shows dropdowns for any indexed pair (`_id` / `_name`). Selecting `[RANDOM]` chooses a unique entity when possible; selecting `[ORDERED]` cycles entities in list order (1..n, then back to 1). The same index is reused wherever it appears.

### C) User-Supplied / Free-Form
- Any placeholder not matched above (e.g., `{mission_name}`, `{area}`) prompts for manual input in the customize dialog.

### D) Random Number Placeholders

**STICKY (same value reused across all occurrences in a task):**
- **Predefined sticky randoms:**
  - `{random_altitude}`, `{random_distance}`, `{random_speed}`, `{random_heading}`
  - `{random_x}`, `{random_y}`, `{random_z}`, `{random_hovertime}`, `{random_duration}`
- **Named variables (sticky):**
  - `{random_var:min:max}`: Named random float
  - `{random_var:min:max:decimals}`: Named random float with decimals
  - `{randint_var:min:max}`: Named random integer
  - `{randx_var}`, `{randy_var}`, `{randz_var}`: Named coordinate variables (with optional ranges)

**ANONYMOUS (new value generated each occurrence):**
- **Base coordinates (no collision avoidance):**
  - `{randx}`: Random X (0-1024)
  - `{randy}`: Random Y (0-768)
  - `{randz}`: Random Z (0-100)
- **Base composite types (with collision avoidance):**
  - `{randxy}`: "x y" (e.g., "127 89")
  - `{randxyc}`: "x, y" (e.g., "127, 89")
  - `{randxyz}`: "x y z" (e.g., "127 89 18")
  - `{randpos}`: "x, y, z" (e.g., "127, 89, 18")
  - Note: These respect safety margins and avoid obstacles
- **Dynamic randoms with custom ranges:**
  - `{random:min:max}`: Anonymous random float
  - `{random:min:max:decimals}`: Anonymous random float with decimals
  - `{randint:min:max}`: Anonymous random integer
  - `{randx:min:max}`, `{randy:min:max}`, `{randz:min:max}`: Anonymous coordinates with custom range

**Variable Coordinate Types (sticky, with optional collision avoidance):**
  - **Variables & Ranges (Strict Colon Syntax):**
    - `{randx_varname}`: Sticky variable. All instances of `{randx_varname}` share the same value.
    - `{randx:min:max}`: Anonymous random with custom range (e.g., `{randx:10:50}`).
    - `{randx_varname:min:max}`: Define variable with range (e.g., `{randx_v1:10:50}`).
    - `{randx_varname:min:max:decimals}`: Define variable with range and decimals.
    - **Note on Priority:** For variables, the FIRST definition determines the value. If you define `{randx_v1:10:20}` and later use `{randx_v1}`, the range 10-20 applies everywhere. If you use `{randx_v1}` (default) first, subsequent definitions of range are ignored for that variable.
  - **Coordinated Position Variables (with collision avoidance):**
    - When `{randx_varname}` and `{randy_varname}` are used together (with optional `{randz_varname}`), they are automatically treated as a coordinated position that avoids obstacles with a safety margin, similar to `{randxy}` and `{randxyz}` composite types.
    - Example: `{randx_target}`, `{randy_target}`, `{randz_target}` will generate a collision-free position.
    - **REQUIREMENT**: This applies only when **BOTH X AND Y** variables share the same variable name. The Z coordinate is optional.
    - **Does NOT work** with:
      - Single coordinates: `{randx_var}` alone → simple random
      - Only X+Z: `{randx_var}`, `{randz_var}` without `{randy_var}` → independent randoms
      - Only Y+Z: `{randy_var}`, `{randz_var}` without `{randx_var}` → independent randoms
    - The safety margin and obstacle avoidance behavior matches that of composite types.
  - **Composite-Scalar Integration (Priority Rule):**
    - **IMPORTANT**: When both a composite type (`{randxy_var}`, `{randxyz_var}`, `{randpos_var}`, `{randxyc_var}`) and scalar coordinates (`{randx_var}`, `{randy_var}`, `{randz_var}`) exist with the **same variable name**, the composite type takes precedence.
    - The position is generated ONCE by the composite type (with collision avoidance), and the scalar components automatically extract their values from the composite.
    - Example: If you use both `{randxy_pos}` and `{randx_pos}`, the system generates one position for `{randxy_pos}` and `{randx_pos}` uses the X component from it.
    - This ensures:
      - No duplicate position generation
      - Perfect consistency between composite and scalar values
      - Single collision check for efficiency
    - **Practical use case**: `"Move to {randxyz_wp}. API call: x={randx_wp}, y={randy_wp}, z={randz_wp}"` - The composite generates the position with collision avoidance, and the API parameters use the same exact values.
    - **Order independence**: The composite always takes precedence, regardless of whether scalar or composite appears first in the template. The system pre-scans all placeholders before generating values.
    - **Variable name matching**: Names must match EXACTLY. `{randx_tar}` + `{randz_alti}` + `{randpos_tar}` → only `{randx_tar}` and `{randy_tar}` would use `{randpos_tar}`, while `{randz_alti}` is independent.
    - **Single scalar behavior**: A lone `{randx_var}` without matching `{randy_var}` or composite generates normally without collision avoidance.
    - **Z coordinate independence**: When using `{randxy_var}` (2D composite) with `{randz_var}`, the Z is generated independently with default range (0-100). To have Z coordinated with XY, use `{randxyz_var}` or `{randpos_var}` composite types.

## 5) How Substitution Works
- Entities: selections fill both `_id` and `_name` placeholders for the same index.
- Randoms: sticky placeholders reuse the same value within a task; anonymous dynamic rerolls per occurrence.
- Related APIs: paths and parameters use the same substitution rules and caches as content/aliases.

## 6) Built-In Templates (reference)
Common built-ins include basic operations and multi-entity missions (examples: `basic_takeoff_land`, `patrol_mission`, `search_task`, `delivery_mission`, `grid_search`, `emergency_return`, `formation_triangle`, `dual_patrol`, `perimeter_search`, `multi_target_survey`). Built-ins are marked `is_builtin: true` and cannot be deleted but can be duplicated/edited into custom versions.

## 7) Examples

**Multi-drone content with randoms**
```
Drone {drone_1_name} and {drone_2_name} inspect {target_1_name} at {random_altitude}m,
then hold at ({random:0:100}, {random:0:100}, {random_altitude}).
```
- `{drone_1_*}` and `{drone_2_*}` come from two distinct dropdown selections.
- `{target_1_name}` from target dropdown.
- `{random_altitude}` sticky within task; `{random:0:100}` rerolls each occurrence.

**Coordinated position variables with collision avoidance**
```
Fly drone {drone_1_name} from ({randx_start}, {randy_start}, {randz_start})
to waypoint ({randx_wp:100:500}, {randy_wp:100:400}, {randz_wp:10:50}).
Return to ({randx_start}, {randy_start}, {randz_start}).
```
- `{randx_start}`, `{randy_start}`, `{randz_start}` form a coordinated group that avoids obstacles.
- `{randx_wp}`, `{randy_wp}`, `{randz_wp}` form another coordinated group with custom ranges.
- All positions are generated to avoid collisions with obstacles and respect safety margins.
- Variables are sticky: `{randx_start}` has the same value throughout the template.

**Composite-scalar integration (efficient position generation)**
```
Navigate to position {randxyz_target}.
Detailed log: Moving to X={randx_target}, Y={randy_target}, Z={randz_target}.
API: POST /drones/{drone_1_id}/move_to with x={randx_target}, y={randy_target}, z={randz_target}
```
- `{randxyz_target}` generates the position ONCE with collision avoidance (e.g., "127 89 18")
- `{randx_target}`, `{randy_target}`, `{randz_target}` automatically extract from the composite (127, 89, 18)
- No duplicate generation - efficient and guaranteed consistent
- Perfect for templates that need both human-readable format and API parameters
- Works with `{randxy_var}`, `{randxyc_var}`, `{randxyz_var}`, and `{randpos_var}`

**API snippet**
```json
{
  "method": "POST",
  "path": "/drones/{drone_1_id}/command/move_to",
  "parameters": {
    "id": "{drone_1_id}",
    "x": "{random_x}",
    "y": "{random_y}",
    "z": "{random_altitude}"
  }
}
```

## 8) Editing Tips and Best Practices
- Keep `_id` and `_name` pairs consistent so the UI can show entity dropdowns.
- Use named randoms when you want one draw reused; use anonymous `{random:...}` when you want different values.
- Reuse placeholders across content, aliases, and APIs for coherent tasks.
- Put every operational placeholder needed to execute the task in both `content` and `content_aliases`, especially route coordinates, target names, obstacle names, thresholds, durations, and distances. Do not hide important waypoint or movement placeholders only in `related_apis` or `execution_check_apis`; the task text is the command the agent reads.
- Test templates after edits by creating a task and verifying substituted values.
- For batch creation, only the task name is auto-numbered; other randoms/entities are drawn per task generation.

## 9) Troubleshooting
- **Placeholder not replaced**: ensure it matches supported patterns and is present in the template; fill required free-form fields.
- **Wrong entity shown**: confirm you used the correct index (`drone_2_id` vs `drone_1_id`) and that both `_id` and `_name` are paired.
- **Random values reused unexpectedly**: named or predefined randoms are sticky; switch to anonymous `{random:min:max}` or `{randint:min:max}` for new rolls per occurrence.
- **Dropdown missing**: the UI only auto-detects placeholders following `_id`/`_name` patterns for drones/targets/obstacles.
- **Composite and scalar values don't match**: Ensure variable names match EXACTLY. `{randx_tar}` and `{randpos_target}` are different variables ('tar' vs 'target'). They won't share values.
- **Z coordinate differs from XY in composite**: If you use `{randxyz_pos}` with `{randx_pos}`, `{randy_pos}`, `{randz_alt}` (different Z name), the Z won't match. Use matching names: `{randxyz_pos}` with `{randz_pos}`.
- **Single randx doesn't avoid obstacles**: A lone `{randx_var}` without `{randy_var}` or composite type won't use collision avoidance. Add `{randy_var}` with the same variable name or use a composite type like `{randxy_var}`.
- **X and Z without Y not coordinated**: `{randx_tar}` + `{randz_tar}` without `{randy_tar}` will NOT be coordinated. Coordination requires BOTH X AND Y. Each generates independently without collision avoidance.
- **Base placeholders vs variables**: `{randx}` (no underscore) is ANONYMOUS (new value each time), NOT sticky. For sticky values, use `{randx_varname}`. For coordinated positions with collision avoidance, use `{randx_varname}` + `{randy_varname}` or composite types like `{randxy_varname}`.
- **randxy composite with independent Z**: `{randxy_pos}` + `{randz_pos}` → XY is coordinated with collision avoidance, but Z generates independently (0-100 range). For fully coordinated 3D position, use `{randxyz_pos}` or `{randpos_pos}`.

## 10) Programmatic Usage (optional)
```python
from task_template_manager import TaskTemplateManager

manager = TaskTemplateManager()
task = manager.instantiate_template('formation_triangle', {
    'name': 'Triangle Patrol',
    'drone_1_id': 'alpha',
    'drone_2_id': 'bravo',
    'drone_3_id': 'charlie'
})
```
- `instantiate_template` applies the same substitution rules used by the GUI.

Use this guide as the canonical reference; other placeholder and template docs can be deleted once this is in place.
