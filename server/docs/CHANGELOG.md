# Changelog

All notable changes to this project should be documented in this file.

## [0.4.1] - 2026-07-03

### Added
- Added an About button to the UI toolbar with version, copyright, license, clickable paper/project/website links, and click-outside dismissal.
- Added UI details-panel vertex coordinate rows for selected polygon targets and obstacles; polygon target details now omit radius and label vertices with the target name.
- Added yellow mini-map selection highlighting for selected drones, targets, and obstacles.

### Changed
- Limited runtime request-history retention to the current session; non-current sessions discard request history by default, and switching the current session clears request history from other sessions.
- Changed request-history `limit` query defaults so omitted `limit` returns all retained records, while explicit `limit` values return that many recent records.
- Excluded `GET /sessions/current/data` from runtime request-history recording.
- Stopped storing full response bodies in structured API logs; logs now record response size, type, and an omission summary, and large response paths skip body capture.

## [0.4.0] - 2026-06-06

### Added
- Added `--ui-drone-control` to opt into UI drone controls, including the Take Off/Land button and map-click movement commands.
- Added `GET /sessions/current/command-history` as a convenience endpoint for retrieving the active session's recent command history.
- Added runtime-only HTTP request history with current-session and explicit-session query endpoints, sensitive-value redaction, and client/authentication audit context.
- Added filtered AGENT access to `GET /sessions/current/request-history` using the non-secret `X-Agent-ID` attribution header.
- Added SYSTEM/ADMIN `DELETE /sessions/current/request-history` and `DELETE /sessions/{id}/request-history` endpoints for clearing runtime request history without resetting sessions.
- Added `--request-history-limit` startup configuration and increased default per-session request-history retention to 5,000 records while keeping API responses capped at 1,000.

### Fixed
- Improved request-history response time by avoiding full response-body capture and normalizing only records needed for each request-history response.
- Preserved replayable request-history query parameters, including ordered repeated keys, sensitive-value redaction, failed requests, and legacy `{}` defaults.
- Excluded request history from serialized session objects, JSON exports, imports, and restores so it remains process-local runtime state.
- Standardized request-history `client_privilege` values on uppercase role names.

## [0.3.9] - 2026-05-23

### Fixed
- Kept the UI path trail length button selection unchanged when the current session reloads and drone-specific path settings are recreated.

## [0.3.8] - 2026-05-10

### Changed
- Added plain `move_along_path` response fields for successful and unsuccessful waypoint counts and `(x, y, z)` coordinate triples.
- Moved `move_along_path` point feedback fields to a dedicated response model so other command schemas do not advertise path-only fields.
- Kept `move_along_path` error responses focused on the error message without populated point feedback values.
- Updated `move_along_path` partial movement responses to return `partial_success` when `allow_partial_move=true` reaches at least one waypoint but stops before the requested endpoint.

## [0.3.6] - 2026-05-03

### Changed
- Updated `move_along_path` to accept 2D `{x, y}` waypoints by defaulting omitted `z` values to the calling drone's current altitude.
- Updated `move_along_path` partial movement so `allow_partial_move=true` stops at the last waypoint with sufficient battery instead of rejecting the whole path when the full route exceeds available battery.
- Updated `move_along_path` battery usage to remove the per-waypoint base cost, making path following charge only horizontal and vertical distance costs.
- Optimized `move_along_path` response time for large waypoint lists by batching internal coverage tracking, reusing path calculations, and avoiding full session history serialization during command recording.
- Updated `move_to` battery usage to remove the base movement cost, matching distance-only movement charging.
- Updated the startup UI prompt to use the same drone window icon as the main graphical dashboard.
- Updated target and obstacle canvas labels to show each object's ID under its type.

## [0.3.4] - 2026-04-25

### Added
- Added multiple hard-coded USER, SYSTEM, and ADMIN privilege keys for API authentication while preserving existing AGENT authentication behavior.
- Added optional `since_timestamp` scoping to task check endpoints so compatible history checks can validate work performed at or after a given timestamp.

### Changed
- Updated authentication documentation and examples to use API key placeholders instead of publishing concrete key values.
- Updated target reach and moving-target tracking check endpoints to support `since_timestamp` filtering.
- Corrected landing history check documentation to describe the implemented `min_count` parameter.
- Updated PyInstaller packaging to include project submodules as hidden imports so frozen Windows builds can import local modules such as `config.battery_config`.

## [0.3.3] - 2026-04-22

### Changed
- Extended ADMIN history check endpoint `GET /check/drone_has_taken_off` to support optional `max_altitude` and `tolerance` query parameters, enabling backward-compatible minimum-threshold checks, bounded altitude-range checks, and exact-height checks via `min_altitude == max_altitude`.
- Updated takeoff history check responses and documentation to include the applied altitude bounds and tolerance metadata.

## [0.3.2] - 2026-04-08

### Added
- Added SVG and EPS export support for session screenshots.
- Added a `show_status` screenshot option that includes path traces, area coverage, reached/tracked target state, and UI-style status bar details.
- Added ADMIN check endpoint `GET /check/drone_group_distance` for validating pairwise distance constraints across a group of drones, with `all_pairs` and `any_pair` modes.
- Added ADMIN check endpoint `GET /check/drone_has_sent_message_content` for validating whether a drone sent message text containing a requested substring, including broadcasts.

### Changed
- Refactored screenshot rendering to use a shared scene model for raster and vector exports.
- Updated screenshot API documentation to cover the new formats and `show_status` query parameter.
- Updated PyInstaller packaging to use the compact executable version format, so app version `0.3.2` builds as `MultiUAV-Plat.Server.v0.32`.
- Updated API reference, API documentation, and authentication docs to describe the new drone-group distance check and repeated-query `drone_ids` usage.
- Updated message-check documentation to describe the new content-matching endpoint and its broadcast-inclusive behavior.
- Updated `move_along_path` to accept `allow_partial_move=false` by default, with optional partial completion that stops at the last safe waypoint before an obstacle and reports the early stop in the success message.
- Updated `move_along_path` to accept a single waypoint, so one-point path requests are handled as a valid path move instead of being rejected.

## [0.3.1] - 2026-04-06

### Added
- Added a cross-platform PyInstaller spec file at `multiuav_plat.spec` for reproducible standalone builds on Windows, macOS, and Linux.
- Added native PyInstaller icon assets at `ui/img/drone.ico` and `ui/img/drone.icns` generated from the existing project icon.

### Changed
- Removed the session `time_mode` attribute from the backend session model, session APIs, example session payloads, and API documentation.
- Updated the standalone deployment documentation in `README.md` to use the shared spec file instead of platform-specific inline PyInstaller commands.
- Corrected the documented UI startup flag for compiled binaries to `--ui`.
- Updated the PyInstaller spec to set the executable icon automatically on Windows and macOS.
- Standardized target and obstacle API payloads on the canonical `type` field instead of legacy `target_type` and `obstacle_type` names across the server contract, tests, README, and API docs.
- Added a toolbar toggle in the UI to show or hide canvas labels for drones, targets, and obstacles.

## [0.3.0] - 2026-04-01

### Added
- Added explicit moving-target runtime fields to target responses:
  - `movement_mode`
  - `last_motion_update`
  - `tracking_status`
  - `last_tracked_at`
- Added backend-owned moving-target tracking state in session history via `moving_target_tracking`.
- Added ADMIN check endpoint `/check/moving_target_tracked` for validating retained moving-target tracking duration for any drone or a specific drone.
- Added dedicated regression tests for moving-target creation, validation, motion stepping, and tracking behavior.
- Added initial project changelog in `docs/CHANGELOG.md`.

### Changed
- Refactored moving-target handling so live target objects are the authoritative runtime source for movement state.
- Refactored session synchronization to use explicit snapshot sync APIs instead of mutating on session reads.
- Updated moving-target motion handling to use explicit internal movement modes:
  - `velocity`
  - `path`
  - `stationary`
- Updated path-based movement to progress deterministically across larger time steps.
- Updated collision behavior for moving targets to apply mode-specific reversal logic.
- Updated `target_tracking` task progress so moving targets use backend freshness-based tracking semantics instead of UI-local timeout logic.
- Enriched `moving_target_tracking` with compact per-drone recent periods so specific-drone duration checks are possible without storing an unbounded raw event log.
- Updated target retrieval paths and UI rendering to consume canonical backend tracking and movement state.
- Updated API documentation and reference docs to describe the new moving-target runtime fields and session tracking payloads.

### Fixed
- Fixed stale moving-target state issues caused by session snapshots lagging behind live simulation state.
- Fixed duplicated movement-mode inference across backend and UI layers.
- Fixed repeated session write/snapshot side effects triggered from drone target-reach loops.
- Fixed path validation gaps by rejecting degenerate moving paths and obstacle-conflicting path segments.
- Fixed inconsistency between historical target reach and current moving-target tracking display.

### Compatibility
- Existing target request payloads remain supported.
- Legacy target response fields such as `is_reached` and `reached_by` remain available for compatibility, but moving-target freshness is now derived from backend tracking state.
