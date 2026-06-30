# UAV Agent API Service

This service provides a REST API for the UAV Control Agent. It allows external applications to send natural language commands to the drone fleet and receive feedback, reasoning steps, and mission status.

## 🚀 Getting Started

### Prerequisites

Ensure you have the required dependencies installed:

```bash
pip install fastapi uvicorn pydantic requests
```

### Starting the Server

Run the server using the new service script:

```bash
python agent_api_service.py
```

The server will start on **port 18000** by default:
- **API Base URL:** `http://localhost:18000`
- **Interactive Documentation (Swagger):** `http://localhost:18000/docs`

---

## 🛠 API Reference

### 1. Asynchronous Execution (Recommended)
Since agent commands can take 1-3 minutes to process, use the async "Job" pattern to avoid timeouts.

**Step 1: Submit Command**
- **Endpoint:** `/agent/command/async`
- **Method:** `POST`
- **Body:** `{"command": "Take off drone-1..."}`
- **Response:**
  ```json
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "message": "Command accepted for background processing"
  }
  ```

**Step 2: Check Status**
- **Endpoint:** `/agent/jobs/{job_id}`
- **Method:** `GET`
- **Response (while running):** `{"status": "running", ...}`
- **Response (completed):**
  ```json
  {
    "job_id": "...",
    "status": "completed",
    "result": {
      "success": true,
      "output": "Drone has taken off...",
      "intermediate_steps": [...] 
    }
  }
  ```

**Step 3: Cancel Job (Optional)**
Stop a running agent command.
- **Endpoint:** `/agent/jobs/{job_id}/cancel`
- **Method:** `POST`
- **Response:** `{"message": "Job ... cancellation requested."}`

### 2. Synchronous Execution (Blocking)
Useful for quick queries, but may timeout for complex tasks.

- **Endpoint:** `/agent/command`
- **Method:** `POST`
- **Body:** `{"command": "Get status"}`

### 3. Get Session Summary
Retrieve the current mission status.

- **Endpoint:** `/agent/session`
- **Method:** `GET`

### 4. Health Check
- **Endpoint:** `/health`
- **Method:** `GET`

---

## 💻 Integration Example (Python)

```python
import requests
import time

BASE_URL = "http://localhost:18000"

def run_async_agent_task(command):
    # 1. Submit Job
    print(f"🚀 Sending command: {command}")
    resp = requests.post(f"{BASE_URL}/agent/command/async", json={"command": command})
    if resp.status_code != 200:
        print(f"Error submitting: {resp.text}")
        return
        
    job_id = resp.json()["job_id"]
    print(f"⏳ Job submitted (ID: {job_id}). Waiting for results...")
    
    # 2. Poll for completion
    try:
        while True:
            status_resp = requests.get(f"{BASE_URL}/agent/jobs/{job_id}")
            job_info = status_resp.json()
            status = job_info["status"]
            
            if status == "completed":
                print("\n✅ Task Completed!")
                print(f"Output: {job_info['result']['output']}")
                break
            elif status == "failed":
                print(f"\n❌ Task Failed: {job_info.get('error')}")
                break
            elif status == "cancelled":
                print("\n🛑 Task Cancelled.")
                break
            else:
                print(f"   Status: {status}...", end="\r")
                time.sleep(2)
    except KeyboardInterrupt:
        # Cancel on Ctrl+C
        print("\n\n⚠️  Interrupted! Cancelling job...")
        requests.post(f"{BASE_URL}/agent/jobs/{job_id}/cancel")
        print("Cancellation sent.")

if __name__ == "__main__":
    run_async_agent_task("Take off drone-1 to 15 meters and inspect the area")
```

---

## ⚙️ Configuration

The server uses `llm_settings.json` for LLM provider configuration. 

**Environment Variables:**
- `UAV_API_URL`: Override UAV simulator URL (Default: `http://localhost:8000`)
- `UAV_API_KEY`: API key for the UAV simulator.
- `OPENAI_API_KEY` / `LLM_API_KEY`: Fallback API keys.

```