import ollama
import json
import os
from typing import Dict, Any, Optional
from core.registry import Registry

class LLMService:
    def __init__(self, registry: Registry):
        self.registry = registry
        self.model = os.getenv("LLM_MODEL", "mistral")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Load System Prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "core", "llm_prompt.md")
        with open(prompt_path, "r") as f:
            self.system_prompt_template = f.read()

    def _get_system_prompt(self) -> str:
        tasks_json = json.dumps(self.registry.list_tasks_for_llm(), indent=2)
        return self.system_prompt_template.replace("{{TASK_REGISTRY_JSON}}", tasks_json)

    async def get_intent(self, user_query: str) -> Dict[str, Any]:
        system_prompt = self._get_system_prompt()
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_query},
                ],
                format='json', # Mistral supports JSON mode in some versions/tags, otherwise we'll parse.
                options={
                    'temperature': 0
                }
            )
            
            content = response['message']['content']
            # Clean up content if it's wrapped in markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"LLM_ERROR: {str(e)}")
            return {
                "error": "LLM_FAILURE",
                "message": "Could not interpret intent via local LLM."
            }
