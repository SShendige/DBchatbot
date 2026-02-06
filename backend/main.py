from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
import os
import json
from dotenv import load_dotenv

# Load environment variables from the root .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from core.registry import Registry
from services.database import DatabaseService
from services.llm_service import LLMService

# Define Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="TOPD Bridge API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple Security Middleware
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY", "dev-key"):
        raise HTTPException(status_code=403, detail="Invalid API Key")

# Initialize Services
registry = Registry("../shared/task_registry.json")
db_service = DatabaseService()
llm_service = LLMService(registry)

class TaskRequest(BaseModel):
    task_id: str
    parameters: Dict[str, Any]

class TaskResponse(BaseModel):
    request_id: str
    status: str
    data: Optional[Any] = None
    report_id: Optional[str] = None
    message: Optional[str] = None

@app.post("/api/execute", response_model=TaskResponse, dependencies=[Depends(verify_api_key)])
async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks):
    return await _run_task_logic(request.task_id, request.parameters, background_tasks)

class ChatRequest(BaseModel):
    query: str

@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def chat_orchestrator(request: Request, chat_req: ChatRequest, background_tasks: BackgroundTasks):
    """
    Calls Ollama Mistral 7B to interpret user intent.
    The LLM outputs task_id + parameters based on the registry.
    """
    intent = await llm_service.get_intent(chat_req.query)
    
    if "error" in intent:
        return {
            "message": intent["message"],
            "data": None
        }

    task_id = intent.get("task_id")
    thought = intent.get("thought", "Interpreting request...")

    # Handle Unsupported or Security Violations
    if task_id == "UNSUPPORTED":
        return {
            "message": "I couldn't identify a specific database task for that request. I can help with sales summaries, top products, or transaction reports.",
            "data": None
        }
    
    if task_id == "SECURITY_VIOLATION":
        return {
            "message": intent.get("message", "Security Protocol Violation."),
            "data": None
        }

    # Handle Missing Parameters (Clarification Flow)
    if "missing_params" in intent:
        return {
            "message": intent.get("clarification_question", "I need more information to process that request."),
            "data": {
                "missing_params": intent["missing_params"],
                "task_id": task_id
            }
        }

    params = intent.get("params", {})

    # Execute the identified task
    result = await _run_task_logic(task_id, params, background_tasks)
    
    return {
        "message": f"{thought} Execution Status: {result.status}.",
        "data": result.dict()
    }

async def _run_task_logic(task_id: str, parameters: Dict[str, Any], background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())
    
    # 1. Validate Task ID
    task_def = registry.get_task(task_id)
    if not task_def:
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id}")

    # 2. Handle Async Reports (Big Data)
    if task_def.is_async:
        report_id = str(uuid.uuid4())
        background_tasks.add_task(run_background_report, report_id, task_id, parameters)
        return TaskResponse(
            request_id=request_id,
            status="accepted",
            report_id=report_id,
            message="Large dataset requested. Report generation started in background."
        )

    # 3. Execute Synchronous Task
    try:
        data = await db_service.execute_task(task_id, parameters)
        return TaskResponse(
            request_id=request_id,
            status="success",
            data=data
        )
    except Exception as e:
        return TaskResponse(
            request_id=request_id,
            status="error",
            message=str(e)
        )

async def run_background_report(report_id: str, task_id: str, params: Dict[str, Any]):
    """
    Simulates a background worker process for large data.
    """
    # Logic:
    # 1. Run huge query
    # 2. Write to CSV/Parquet in secure storage
    # 3. Mark report as complete in a separate status table
    print(f"BKG_JOB: Generating report {report_id} for task {task_id}")
    pass

@app.get("/api/registry")
async def get_registry_for_llm():
    """
    Endpoint for the LLM to fetch its capabilities.
    """
    return registry.list_tasks_for_llm()
