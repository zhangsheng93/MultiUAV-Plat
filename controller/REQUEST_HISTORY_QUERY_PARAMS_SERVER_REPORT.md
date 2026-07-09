# Server Change Request: Preserve Query Parameters in Request History

## Summary

The request-history API does not currently preserve URL query parameters. As a result, exported request-history records cannot reliably replay endpoints whose required inputs are supplied through the query string.

Please add an optional `query_params` object to every request-history record. This is an additive, backward-compatible schema change. Existing fields and endpoint behavior should remain unchanged.

Affected endpoints:

```http
GET /sessions/current/request-history?limit=1000
GET /sessions/{session_id}/request-history?limit=1000
```

## Observed Failure

The GUI exported this file:

```text
/Users/victor/Downloads/Path_Planning_Moderate_5-selected_entries.jsonl
```

It contains records such as:

```json
{
  "request_id": "3a9143e5-ef24-4e25-a84c-11ed255ec510",
  "timestamp": "2026-06-24T15:57:48.859676Z",
  "method": "POST",
  "path": "/drones/1ccd9c76/command/move_to",
  "request_body": null,
  "status_code": 200,
  "success": true,
  "duration_sec": 0.009749,
  "response_body": {
    "command_id": "f68121c1",
    "drone_id": "1ccd9c76",
    "command": "move_to",
    "status": "success"
  },
  "error": null
}
```

The original request succeeded because the direct command endpoint received required query parameters:

```http
POST /drones/1ccd9c76/command/move_to?x=451&y=600&z=21
```

However, neither the saved `path` nor `request_body` contains those values. Replaying the exported record sends:

```http
POST /drones/1ccd9c76/command/move_to
```

The server then correctly returns:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "x"],
      "msg": "Field required",
      "input": null
    },
    {
      "type": "missing",
      "loc": ["query", "y"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

This problem affects any endpoint whose inputs are carried in the query string, including direct commands such as:

- `move_to`
- `take_off`
- `move_towards`
- `change_altitude`
- `rotate`
- `hover`
- `send_message`
- `broadcast`
- `charge`

It can also affect non-command GET, POST, PUT, PATCH, or DELETE endpoints that use query parameters.

## Required Response Schema

Add `query_params` to each request-history record:

```json
{
  "request_id": "3a9143e5-ef24-4e25-a84c-11ed255ec510",
  "timestamp": "2026-06-24T15:57:48.859676Z",
  "method": "POST",
  "path": "/drones/1ccd9c76/command/move_to",
  "query_params": {
    "x": 451,
    "y": 600,
    "z": 21
  },
  "request_body": null,
  "status_code": 200,
  "success": true,
  "duration_sec": 0.009749,
  "response_body": {
    "command_id": "f68121c1",
    "drone_id": "1ccd9c76",
    "command": "move_to",
    "status": "success"
  },
  "error": null
}
```

For a request without query parameters:

```json
"query_params": {}
```

The canonical field name must be `query_params`.

## Server Implementation Requirements

### Capture

- Capture query parameters from the incoming HTTP request before endpoint execution.
- Store the parameters in the request-history record associated with that request.
- Do not append the query string to `path`; keep `path` as the existing route path.
- Record query parameters for successful and failed requests.
- Record query parameters for every supported HTTP method.

### Value Representation

- Preserve scalar values in their normal JSON-compatible representation when practical.
- Preserve repeated query keys as arrays instead of discarding values.

For example:

```http
GET /example?tag=alpha&tag=beta&limit=10
```

should produce:

```json
{
  "query_params": {
    "tag": ["alpha", "beta"],
    "limit": "10"
  }
}
```

It is acceptable for raw HTTP query values to remain strings. The important requirement is that replaying the stored values reproduces the original query string.

### Redaction

- Apply the same sensitive-value redaction policy currently used for request and response bodies.
- Redact sensitive query keys case-insensitively.
- Cover at least API keys, authorization values, access tokens, refresh tokens, passwords, secrets, and session tokens.
- Redact each element when a sensitive key has repeated values.

Example:

```json
{
  "query_params": {
    "api_key": "[REDACTED]",
    "target_id": "target-1"
  }
}
```

### Persistence

- Include `query_params` in in-memory session request-history records.
- Include it in:
  - `GET /sessions/current/request-history`
  - `GET /sessions/{session_id}/request-history`
  - complete session exports
  - restored/imported sessions
- Preserve it through session save, export, restore, and duplication paths where request history is retained.
- Continue enforcing the existing 1,000-record retention behavior.

### Legacy Data

- Older stored records may not contain `query_params`.
- Deserialization and response serialization must accept missing values and treat them as `{}`.
- Do not reject or rewrite an entire legacy session because request-history entries lack this field.

Suggested model behavior:

```python
query_params: dict[str, object] = Field(default_factory=dict)
```

Use the equivalent construct for the server's actual framework and model layer.

## Backward Compatibility

This change should not break existing clients because it is additive:

- Do not remove, rename, or change the meaning of any existing field.
- Do not change either request-history endpoint path.
- Do not change the response wrapper:

```json
{
  "request_history": []
}
```

- Add only the optional `query_params` field within each history entry.
- Use `{}` as the default for newly serialized records with no query parameters.
- Accept missing `query_params` when loading old records.

Most JSON clients ignore unknown fields. Potential compatibility risks are limited to strict clients that reject additional properties, exact-response snapshot tests, and code comparing complete dictionaries. Please update those schemas or fixtures to declare `query_params` as optional.

A versioned endpoint or opt-in flag is not recommended unless a known deployed client rejects additive response fields.

## Client Integration Context

After the server supplies `query_params`, the GUI will normalize a history entry as:

```python
{
    "method": entry["method"],
    "endpoint": entry["path"],
    "payload": entry.get("request_body"),
    "params": entry.get("query_params") or {},
}
```

It will replay the request through the existing client interface:

```python
api_generic_request(
    method,
    endpoint,
    payload,
    params=params,
)
```

No server-side replay endpoint is requested. The server only needs to preserve the original request inputs accurately.

## API Documentation Changes

Update the request-history record example to include:

```json
"query_params": {}
```

Document that:

- `query_params` contains the original redacted query-string values.
- Repeated keys are represented as arrays.
- Records created before this server change may omit the field.
- Missing `query_params` is equivalent to `{}`.

Add the change to the server changelog as a backward-compatible request-history schema enhancement.

## Acceptance Tests

### Direct Command with Query Parameters

1. Send:

   ```http
   POST /drones/{id}/command/move_to?x=451&y=600&z=21
   ```

2. Read current-session request history.
3. Verify the matching record contains:

   ```json
   {
     "path": "/drones/{id}/command/move_to",
     "query_params": {
       "x": "451",
       "y": "600",
       "z": "21"
     },
     "request_body": null
   }
   ```

Numeric values are also acceptable if the server intentionally performs typed conversion.

### JSON Body and Query Parameters Together

Send a request containing both a JSON body and query parameters. Verify both `request_body` and `query_params` are preserved independently.

### No Query Parameters

Send a request without a query string. Verify the new record contains:

```json
"query_params": {}
```

### Failed Request

Send a request with invalid query values that returns `4xx`. Verify the attempted query parameters are still recorded.

### Repeated Query Keys

Send:

```http
GET /example?tag=alpha&tag=beta
```

Verify:

```json
"query_params": {
  "tag": ["alpha", "beta"]
}
```

### Sensitive Query Values

Send a request containing both sensitive and non-sensitive query keys. Verify sensitive values are redacted and ordinary values remain available.

### Export and Restore

1. Create request-history records containing query parameters.
2. Export the session.
3. Restore the session.
4. Verify `query_params` remains unchanged.

### Legacy Session

Load a session containing request-history records without `query_params`. Verify:

- The session loads successfully.
- The request-history endpoints return those records.
- Missing values are exposed as either absent or `{}` according to the server's serialization policy.
- New records contain `query_params`.

### Existing Client Compatibility

- Run existing request-history endpoint tests.
- Run strict response-model and snapshot tests.
- Verify all pre-existing fields retain their previous values and types.

## Definition of Done

The server change is complete when:

- Newly recorded requests retain all original query parameters.
- Sensitive query values are redacted.
- Repeated keys are not lost.
- Query parameters survive export and restore.
- Legacy sessions continue to load.
- Existing request-history clients remain compatible.
- A newly exported GUI history file can replay a `move_to` request without receiving a missing `x` or `y` validation error.

## Limitation of Existing Exports

Existing JSONL files created before this server change cannot be made fully replayable from request history alone because their query parameters were never recorded.

The GUI may attempt best-effort recovery for drone commands by matching `response_body.command_id` against command history, but this is not reliable for every request type. New request-history records and exports created after the server change will be the authoritative fix.
