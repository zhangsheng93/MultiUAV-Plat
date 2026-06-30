import uvicorn
import os
import uuid
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# LangChain imports for cancellation
from langchain_core.callbacks import BaseCallbackHandler

# Import your existing project modules
from uav_agent import UAVControlAgent, bool_setting, load_llm_settings
from logging_config import get_logger

logger = get_logger("agent_api_service")

# ------------------------------------------------------------------ #
# Data Models
# ------------------------------------------------------------------ #
class CommandRequest(BaseModel):
    command: str

class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0

class CommandResponse(BaseModel):
    success: bool
    output: str
    intermediate_steps: List[Any] = []
    token_usage: Optional[TokenUsage] = None

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AsyncCommandResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Command accepted for background processing"

class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    command: str
    result: Optional[CommandResponse] = None
    error: Optional[str] = None

class SessionSummaryResponse(BaseModel):
    summary: str

class HealthResponse(BaseModel):
    status: str
    agent_initialized: bool
    model: Optional[str] = None
    provider: Optional[str] = None

def make_json_safe(value: Any) -> Any:
    """
    Convert agent/runtime objects into data structures Pydantic can serialize.

    LangChain tool steps can contain SimpleNamespace action objects. They are
    useful internally, but FastAPI/Pydantic v2 cannot emit them directly in a
    response_model.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseModel):
        return make_json_safe(value.model_dump())
    if isinstance(value, SimpleNamespace):
        return make_json_safe(vars(value))
    if is_dataclass(value) and not isinstance(value, type):
        return make_json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, Exception):
        return str(value)
    if hasattr(value, "__dict__"):
        return make_json_safe(vars(value))
    return str(value)

def command_response_from_result(result_data: Dict[str, Any]) -> CommandResponse:
    raw_token_usage = result_data.get("token_usage")
    token_usage = TokenUsage(**raw_token_usage) if isinstance(raw_token_usage, dict) else None
    return CommandResponse(
        success=bool(result_data.get("success", False)),
        output=str(result_data.get("output", "")),
        intermediate_steps=make_json_safe(result_data.get("intermediate_steps", [])),
        token_usage=token_usage,
    )

# ------------------------------------------------------------------ #
# Global State & Lifecycle
# ------------------------------------------------------------------ #
agent_instance: Optional[UAVControlAgent] = None
AGENT_CONFIG_FILE = "llm_settings.json"
jobs: Dict[str, JobInfo] = {}

class JobCancelledException(Exception):
    """Raised when a job is cancelled by the user."""
    pass

class CancellationCallback(BaseCallbackHandler):
    """
    LangChain callback that checks if a job has been cancelled.
    If so, it raises an exception to stop execution.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id

    def _check_cancellation(self):
        job = jobs.get(self.job_id)
        if job and job.status == JobStatus.CANCELLED:
            raise JobCancelledException(f"Job {self.job_id} was cancelled by user.")

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        self._check_cancellation()

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        self._check_cancellation()

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        self._check_cancellation()

def initialize_agent_from_settings() -> UAVControlAgent:
    """
    Reads llm_settings.json and initializes the UAVControlAgent.
    """
    settings = load_llm_settings(AGENT_CONFIG_FILE)
    if not settings:
        raise RuntimeError(f"Could not load settings from {AGENT_CONFIG_FILE}")

    selected_provider_name = settings.get("selected_provider")
    if not selected_provider_name:
        raise RuntimeError("No 'selected_provider' found in settings.")

    provider_configs = settings.get("provider_configs", {})
    config = provider_configs.get(selected_provider_name)
    if not config:
        raise RuntimeError(f"Configuration for provider '{selected_provider_name}' not found.")

    provider_type = config.get("type", "ollama")
    base_url = config.get("base_url", "").strip()
    model = config.get("default_model", "")
    api_key = str(config.get("api_key", "") or "").strip()
    
    if provider_type == "ollama":
        llm_provider = "ollama"
        llm_base_url = None
    else:
        if "api.openai.com" in base_url:
            llm_provider = "openai"
        else:
            llm_provider = "openai-compatible"
        llm_base_url = base_url or None

    if config.get("requires_api_key") and not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise RuntimeError(f"Provider '{selected_provider_name}' requires an API key.")

    logger.info(f"Initializing Agent with Provider: {selected_provider_name}, Model: {model}")
    
    uav_base_url = (
        os.getenv("UAV_API_URL")
        or str(settings.get("uav_base_url", "") or "").strip()
        or "http://localhost:8000"
    )
    uav_api_key = (
        os.getenv("UAV_API_KEY")
        or str(settings.get("uav_api_key", "") or "").strip()
        or None
    )
    share_blackboard_by_session = bool_setting(
        settings.get("share_blackboard_by_session"),
        default=False,
    )
    toolchain_json_recording = bool_setting(
        settings.get("toolchain_json_recording"),
        default=False,
    )
    logger.info(
        "Agent blackboard sharing by session: %s",
        share_blackboard_by_session,
    )
    logger.info(
        "Agent tool-chain JSON recording: %s",
        toolchain_json_recording,
    )

    return UAVControlAgent(
        base_url=uav_base_url,
        uav_api_key=uav_api_key,
        llm_provider=llm_provider,
        llm_model=model,
        llm_api_key=api_key or None,
        llm_base_url=llm_base_url,
        temperature=0.1,
        verbose=True,
        debug=False,
        share_blackboard_by_session=share_blackboard_by_session,
        toolchain_json_recording=toolchain_json_recording,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_instance
    try:
        logger.info("Attempting to initialize UAV Agent...")
        agent_instance = initialize_agent_from_settings()
        logger.info("UAV Agent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize UAV Agent: {e}")
    yield
    agent_instance = None
    logger.info("UAV Agent Server shutting down.")

# ------------------------------------------------------------------ #
# FastAPI App
# ------------------------------------------------------------------ #
app = FastAPI(
    title="UAV Agent API Service",
    description="REST API interface for the UAV Control Agent with Async Job Support",
    version="1.2.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    if agent_instance:
        return HealthResponse(status="active", agent_initialized=True, provider="configured")
    return HealthResponse(status="warning", agent_initialized=False, provider=None)

def process_agent_command(job_id: str, command: str):
    """
    Background task wrapper with cancellation support.
    """
    global jobs
    job = jobs.get(job_id)
    if not job:
        return

    if job.status == JobStatus.CANCELLED:
        logger.info(f"Job {job_id} cancelled before start.")
        return

    job.status = JobStatus.RUNNING
    logger.info(f"Starting processing for Job {job_id}")
    
    try:
        if not agent_instance:
             raise RuntimeError("Agent not initialized")
             
        # Use the callback to detect cancellation during execution
        cancel_callback = CancellationCallback(job_id)
        
        # This requires UAVControlAgent.execute to accept 'callbacks'
        result_data = agent_instance.execute(command, callbacks=[cancel_callback])
        
        # Double check in case it was cancelled at the very end
        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} was cancelled during execution.")
            return

        job.result = command_response_from_result(result_data)
        job.status = JobStatus.COMPLETED
        logger.info(f"Job {job_id} completed successfully.")

    except JobCancelledException:
        logger.info(f"Job {job_id} execution stopped by user cancellation.")
        # Status is already updated to CANCELLED by the endpoint
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job.error = str(e)
        job.status = JobStatus.FAILED
    finally:
        job.completed_at = datetime.now()

@app.post("/agent/command/async", response_model=AsyncCommandResponse)
async def execute_command_async(request: CommandRequest, background_tasks: BackgroundTasks):
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    command = request.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    job_id = str(uuid.uuid4())
    job = JobInfo(
        job_id=job_id,
        status=JobStatus.QUEUED,
        created_at=datetime.now(),
        command=command
    )
    jobs[job_id] = job
    
    background_tasks.add_task(process_agent_command, job_id, command)
    
    return AsyncCommandResponse(job_id=job_id, status=JobStatus.QUEUED)

@app.post("/agent/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running or queued job.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        return {"message": f"Job {job_id} is already finished ({job.status})."}
        
    if job.status == JobStatus.CANCELLED:
        return {"message": f"Job {job_id} is already cancelled."}

    previous_status = job.status
    job.status = JobStatus.CANCELLED
    logger.info(f"Cancellation requested for Job {job_id} (was {previous_status})")
    
    return {"message": f"Job {job_id} cancellation requested."}

@app.get("/agent/jobs/{job_id}", response_model=JobInfo)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.post("/agent/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """Synchronous execution (Blocking)"""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return command_response_from_result(agent_instance.execute(request.command))

@app.get("/agent/session", response_model=SessionSummaryResponse)
async def get_session_summary():
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        summary = agent_instance.get_session_summary()
        return SessionSummaryResponse(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("\n🚀 Starting UAV Agent API Service on http://0.0.0.0:18000")
    uvicorn.run(app, host="0.0.0.0", port=18000)
