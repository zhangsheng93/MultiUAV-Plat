# Task Generator

Task generation is available in several places. Use the workflow that matches the number of sessions and the amount of control you need.

For full template syntax, placeholders, random values, and template editing rules, see the [Task Template Editing Guide](../API_doc/TASK_TEMPLATE_EDIT_GUIDE.md).

## Generation Options

- New session creation: optionally creates tasks from templates while creating a session.
- Session GUI Controller `From Template`: creates tasks from a selected template in the current session.
- Session GUI Controller `RandomGen`: creates random tasks from compatible templates in the current session.
- Session Manager `TaskUI`: creates tasks from one template across multiple sessions.

## New Session Auto Task Generation

Use this when creating new generated sessions.

1. Open the Session Manager with `python main.py`.
2. Click `New`.
3. Choose the session name, task type, area size, and initialization mode.
4. Enable `Create tasks from templates`.
5. Set `Task Num`.
6. Click `Create` or `Create Batch`.

The generator selects templates suitable for the session task type and fills compatible drone, target, and obstacle placeholders from the session data.

## Create From Template in the Controller

Use this when you want to choose a specific template for one current session.

1. Open a session with `Launch`.
2. Open the `Tasks` tab.
3. Click `From Template`.
4. Select a template in the Task Template Browser.
5. Fill required parameters in the customization dialog.
6. Click `Create Task`, or use batch creation if offered by the dialog.

The template browser supports built-in and custom templates. Built-in templates can be duplicated when you need a customized version.

## RandomGen in the Controller

Use this when you want the controller to create random tasks from compatible templates.

1. Open a session with `Launch`.
2. Open the `Tasks` tab.
3. Click `RandomGen`.
4. Enter the number of tasks to generate.
5. Confirm the dialog.

If no tasks are created, the most common causes are:

- No template is suitable for the session task type.
- Suitable templates exist but require drones, targets, or obstacles that the session does not have.
- Template placeholders cannot be resolved from the current session data.

## Multi-Session TaskUI

Use this when you want to apply a template across several sessions.

1. Open the Session Manager.
2. Click `TaskUI`.
3. Click `Use Template`.
4. Select one or more sessions.
5. Choose a template.
6. Fill template parameters.
7. Create tasks for the selected sessions.

TaskUI builds a union of available drones, targets, and obstacles from selected sessions for parameter selection, then resolves values per session during creation.

## Template Compatibility Rules

A template can be generated automatically when:

- Its `suitable_task` is empty, includes `all`, or matches the session task type.
- All required entity placeholders can be filled from the session.
- Drone placeholders require available drones.
- Target placeholders require available targets.
- Obstacle placeholders require available obstacles.

Entity placeholders include names such as:

- `{drone_id}`, `{drone_name}`, `{drone_1_id}`, `{drone_1_name}`
- `{target_id}`, `{target_name}`, `{target_1_id}`, `{target_1_name}`
- `{obstacle_id}`, `{obstacle_name}`, `{obstacle_1_id}`, `{obstacle_1_name}`

Random placeholders are filled by the template system. See the [Task Template Editing Guide](../API_doc/TASK_TEMPLATE_EDIT_GUIDE.md) for the complete placeholder reference.

## Checking Generated Tasks

After generation:

1. Open the `Tasks` tab.
2. Select a generated task.
3. Inspect its content and related APIs.
4. Use `Check` if the task has `execution_check_apis`.
5. Use [AI Agent Checker](ai-agent-checker.md) for automated queue-based checking.

## Troubleshooting

- If a template does not appear, check whether its `suitable_task` matches the current session task type.
- If entity dropdowns are missing, verify the template uses supported `_id` and `_name` placeholder patterns.
- If generated task names collide, the app auto-numbers new names where supported.
- If checks cannot run, add or fix `execution_check_apis` in the task or template.
