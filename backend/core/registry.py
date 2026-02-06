from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import os

class TaskParameter(BaseModel):
    type: str
    description: str
    default: Optional[Any] = None
    enum: Optional[List[str]] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None

class TaskDefinition(BaseModel):
    task_id: str
    description: str
    parameters: Dict[str, TaskParameter]
    max_rows: Optional[int] = 1000
    priority: str = "normal"
    is_async: bool = Field(default=False, alias="async")

class Registry:
    def __init__(self, path: str):
        with open(path, 'r') as f:
            data = json.load(f)
            self.tasks: Dict[str, TaskDefinition] = {
                t['task_id']: TaskDefinition(**t) for t in data['tasks']
            }

    def get_task(self, task_id: str) -> Optional[TaskDefinition]:
        return self.tasks.get(task_id)

    def list_tasks_for_llm(self) -> List[Dict]:
        # Strip internal metadata before sending to LLM
        return [
            {
                "task_id": t.task_id,
                "description": t.description,
                "parameters": {k: v.dict(exclude_none=True) for k, v in t.parameters.items()}
            }
            for t in self.tasks.values()
        ]
