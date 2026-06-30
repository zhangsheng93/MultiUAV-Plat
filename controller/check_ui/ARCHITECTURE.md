# AI Agent Auto-Check - Architecture Documentation

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   AI Agent Auto-Check UI                        │
│                      (Tkinter Application)                       │
│                                                                  │
│  ┌────────────────┐                  ┌─────────────────────┐   │
│  │  Selection     │                  │  Control & Progress │   │
│  │  Panel         │                  │  Panel              │   │
│  │                │                  │                     │   │
│  │ • Sessions     │                  │ • Options           │   │
│  │ • Tasks Tree   │                  │ • Control Buttons   │   │
│  │ • Queue List   │                  │ • Progress Bar      │   │
│  └────────────────┘                  │ • Log Area          │   │
│                                       └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
           │                                      │
           │ API Calls                            │ Agent Calls
           ▼                                      ▼
┌──────────────────────┐              ┌──────────────────────┐
│   API Server         │              │   Agent Server       │
│   (Port 8000)        │              │   (Port 18000)       │
│                      │              │                      │
│ • Sessions API       │              │ • Async Commands     │
│ • Tasks API          │              │ • Job Status         │
│ • Drones API         │              │ • LLM Integration    │
│ • Check Execution    │              │                      │
└──────────────────────┘              └──────────────────────┘
```

## Component Architecture

### 1. AgentCheckerApp (Main Application)

```
AgentCheckerApp
├── UI Layer (Tkinter)
│   ├── Selection Panel
│   │   ├── Sessions Listbox
│   │   ├── Tasks Treeview
│   │   └── Queue Listbox
│   └── Control Panel
│       ├── Options (Force Land Checkbox)
│       ├── Control Buttons (Start/Pause/Resume/Stop)
│       ├── Progress Display
│       └── Log Text Widget
│
├── Data Layer
│   ├── sessions_data: List[Dict]
│   ├── all_tasks_data: Dict[session_id, List[Task]]
│   ├── selected_tasks: List[Tuple]
│   └── task_check_results: Dict[Tuple, Result]
│
├── Control Layer
│   ├── Workflow State (is_running, is_paused, stop_requested)
│   ├── Worker Thread
│   └── Progress Tracking
│
└── Integration Layer
    ├── api_server: APIServer
    └── agent_client: AgentClient
```

### 2. AgentClient (Agent Communication)

```
AgentClient
├── Session Management
│   └── requests.Session (persistent HTTP)
│
├── Core Methods
│   ├── check_health() → bool
│   ├── submit_command_async(cmd) → job_info
│   ├── get_job_status(job_id) → status_info
│   ├── wait_for_completion(job_id) → (success, result)
│   └── submit_and_wait(cmd) → (success, result)
│
└── Configuration
    ├── base_url (default: http://localhost:18000)
    └── logger
```

### 3. APIServer Integration

```
APIServer (Modified)
├── Existing Methods (Reused)
│   ├── api_get_sessions()
│   ├── api_get_current_session_tasks()
│   ├── api_get_session_task(session_id, task_id)
│   ├── api_set_session_as_current(session_id)
│   ├── api_check_execution(endpoint, params)
│   └── api_mark_task_done(session_id, task_id)
│
└── New Method (Added)
    └── api_land_all_drones() → result
```

## Data Flow Diagrams

### Session & Task Loading Flow

```
User Action          Application                  API Server
    │                     │                           │
    ├─ Click "Refresh" ──>│                           │
    │                     ├─ api_get_sessions() ───>  │
    │                     │<────── sessions ──────────┤
    │                     ├─ Update UI                │
    │                     │                           │
    ├─ Select Session ───>│                           │
    │                     ├─ api_set_session_current()>│
    │                     ├─ api_get_current_tasks() >│
    │                     │<────── tasks ─────────────┤
    │                     ├─ Populate Tree            │
    │                     │                           │
    ├─ Select Tasks ─────>│                           │
    ├─ Add to Queue ─────>│                           │
    │                     ├─ Update Queue List        │
```

### Automated Checking Workflow

```
Start Button         Main Thread          Worker Thread        Agent Server
    │                     │                     │                    │
    ├──── Click ─────────>│                     │                    │
    │                     ├── Spawn Thread ────>│                    │
    │                     │                     │                    │
    │                     │                     ├── For Each Task    │
    │                     │                     │                    │
    │                     │                     ├─ Land Drones? ─────┤
    │                     │                     │   (if enabled)     │
    │                     │                     │                    │
    │                     │                     ├─ Get Command       │
    │                     │                     │                    │
    │                     │                     ├─ submit_async() ──>│
    │                     │                     │<─── job_id ────────┤
    │                     │<── Update UI ───────┤                    │
    │                     │                     │                    │
    │                     │                     ├─ Poll (every 5s)──>│
    │                     │<── Update Status ───┤<─── status ────────┤
    │                     │                     │  (running...)      │
    │                     │                     │                    │
    │                     │                     ├─ Poll ────────────>│
    │                     │<── Update Status ───┤<─── completed ─────┤
    │                     │                     │                    │
    │                     │                     ├─ Check Task        │
    │                     │                     │   Completion        │
    │                     │<── Update Result ───┤                    │
    │                     │                     │                    │
    │                     │                     └─ Next Task         │
    │                     │<── Complete ────────┤                    │
    │                     ├── Show Summary      │                    │
```

### Task Checking Flow

```
Worker Thread              API Server                 Task Logic
    │                          │                          │
    ├─ Get execution_check ───>│                          │
    │<─── check_apis ───────────┤                          │
    │                          │                          │
    ├─ Evaluate Tree ──────────────────────────────────────>│
    │                          │                          │
    │                          │                    ┌─────┴─────┐
    │                          │                    │ Group?    │
    │                          │                    └─────┬─────┘
    │                          │                      Yes │ No
    │                          │                    ┌─────▼─────┐
    │                          │              ┌─────┤ AND/OR/NOT│
    │                          │              │     └───────────┘
    │                          │              │     Recurse children
    │                          │              │            │
    │                          │              │     ┌──────▼──────┐
    │                          │              └────>│ Make API Call│
    │                          │                    └──────┬──────┘
    │                          │<── api_check_execution() ─┤
    │                          ├─── Check Result ─────────>│
    │                          │<── response ───────────────┤
    │<─────── (result, details) ─────────────────────────────┤
    │                          │                          │
    ├─ Record Result           │                          │
```

## Threading Model

### Thread Safety Design

```
┌─────────────────────────────────────────────────┐
│              Main Thread (Tkinter)               │
│                                                  │
│  • All UI operations                             │
│  • Event handling                                │
│  • UI updates via root.after(0, callback)        │
│                                                  │
│  State Variables (shared, read by worker):       │
│  • is_paused                                     │
│  • stop_requested                                │
│                                                  │
└──────────────────┬──────────────────────────────┘
                   │
                   │ spawn / join
                   │
┌──────────────────▼──────────────────────────────┐
│            Worker Thread (Background)            │
│                                                  │
│  • Task queue processing                         │
│  • Agent communication                           │
│  • API calls                                     │
│  • Check evaluation                              │
│                                                  │
│  UI Updates (via root.after):                    │
│  • self.root.after(0, lambda: self.log(...))     │
│  • self.root.after(0, lambda: update_progress()) │
│                                                  │
└──────────────────────────────────────────────────┘

Thread Communication:
├── Main → Worker: State flags (is_paused, stop_requested)
└── Worker → Main: UI updates via root.after(0, callback)
```

### State Machine

```
         ┌─────────┐
         │  IDLE   │
         └────┬────┘
              │
      Click Start
              │
         ┌────▼────┐
         │ RUNNING │◄────────┐
         └────┬────┘         │
              │              │
      Click Pause    Click Resume
              │              │
         ┌────▼────┐         │
         │ PAUSED  │─────────┘
         └────┬────┘
              │
       Click Stop
              │
         ┌────▼────┐
         │ STOPPED │
         └────┬────┘
              │
      Auto Complete
              │
         ┌────▼────┐
         │ IDLE    │
         └─────────┘
```

## Module Dependencies

```
agent_checker.py
    ├── tkinter (stdlib)
    ├── threading (stdlib)
    ├── json (stdlib)
    ├── hashlib (stdlib)
    ├── datetime (stdlib)
    │
    ├── agent_client.py (new)
    │   ├── requests (external)
    │   ├── time (stdlib)
    │   └── logging (stdlib)
    │
    ├── api_server.py (modified)
    │   ├── requests (external)
    │   └── app_settings.py
    │
    └── utils.py (reused)
        ├── json (stdlib)
        ├── pathlib (stdlib)
        └── tkinter (stdlib)
```

## File Organization

```
check_ui/
│
├── Python Modules
│   ├── __init__.py              # Package init
│   ├── agent_client.py          # Agent API wrapper
│   ├── agent_checker.py         # Main application
│   └── run_agent_checker.py     # Launcher
│
└── Documentation
    ├── README.md                # Full documentation
    ├── QUICK_START.md           # Quick reference
    ├── ARCHITECTURE.md          # This file
    ├── IMPLEMENTATION_SUMMARY.md # Implementation notes
    └── AGENT_README_API.md      # Agent API docs
```

## External Interfaces

### API Server Interface (Port 8000)

```
GET  /sessions                          → List sessions
POST /sessions/{id}/set-current         → Set current session
GET  /sessions/current/tasks            → Get tasks
GET  /sessions/{sid}/tasks/{tid}        → Get task details
GET  /check/execution?endpoint=...      → Execute check
PUT  /sessions/{sid}/tasks/{tid}/done   → Mark task done
POST /drones/land_all                   → Land all drones (NEW)
```

### Agent Server Interface (Port 18000)

```
GET  /health                            → Health check
POST /agent/command/async               → Submit command
     Body: {"command": "..."}
     Response: {"job_id": "...", "status": "queued"}

GET  /agent/jobs/{job_id}               → Get job status
     Response: {"status": "running|completed|failed", "result": {...}}

GET  /agent/session                     → Get session summary
```

## Error Handling Strategy

```
Level 1: UI Layer
    ├── User-friendly error messages
    ├── Graceful degradation
    └── messagebox.showerror()

Level 2: Application Layer
    ├── Try-catch around major operations
    ├── Log errors with context
    └── Update UI status

Level 3: Client Layer (AgentClient, APIServer)
    ├── Network error handling
    ├── Timeout handling
    ├── Retry logic (in APIServer)
    └── Return None on failure

Level 4: Worker Thread
    ├── Catch all exceptions
    ├── Continue to next task
    ├── Record failure in results
    └── Never crash thread
```

## Performance Considerations

### Polling Optimization
- **Interval**: 5 seconds (balance between responsiveness and server load)
- **Timeout**: 300 seconds (5 minutes) per task
- **Thread**: Background thread prevents UI blocking

### Memory Management
- **Session data**: Loaded on demand
- **Task data**: Cached per session
- **Results**: Held in memory until export
- **Clear strategy**: Manual queue clearing

### UI Responsiveness
- **Threading**: All long operations in background
- **Updates**: Batched via root.after()
- **Log**: Automatic scrolling with text limit

## Security Considerations

1. **API Authentication**: Uses api_key from settings
2. **Input Validation**: API server validates all inputs
3. **Thread Safety**: Proper synchronization
4. **Error Exposure**: Errors logged but not exposed to user in detail

## Extension Points

### Easy to Extend

1. **Add new agent commands**: Modify command selection logic
2. **Custom check logic**: Extend evaluate_execution_check_node()
3. **Additional UI panels**: Add to setup_ui()
4. **Export formats**: Add new export methods
5. **Status callbacks**: Extend status_callback in wait_for_completion()

### Requires More Work

1. **Parallel execution**: Needs thread pool implementation
2. **Database persistence**: Requires DB integration
3. **Real-time streaming**: Needs WebSocket support
4. **Distributed checking**: Needs network coordination

## Conclusion

The architecture is designed to be:
- **Modular**: Clear separation of concerns
- **Maintainable**: Well-documented and organized
- **Extensible**: Easy to add new features
- **Robust**: Comprehensive error handling
- **User-friendly**: Responsive UI with clear feedback

The system successfully integrates with existing project infrastructure while maintaining independence and avoiding breaking changes.
