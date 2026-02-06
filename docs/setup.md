# Setup Instructions

## Prerequisites
- Python 3.9+
- FastAPI, Uvicorn, Pydantic, Ollama (Python lib)
- [Ollama](https://ollama.com/) installed and running locally
- Mistral 7B model pulled: `ollama pull mistral`

## Installation

1. **Clone and enter directory**:
   ```bash
   cd dbcbot
   ```

2. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn pydantic
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your DB credentials.
   ```bash
   cp .env.example .env
   ```

4. **Run the Backend**:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8001
   ```

## Integration with LLM
To connect an LLM (e.g., GPT-4, Gemini):
1. Fetch the registry from `GET /api/registry`.
2. Inject it into the system prompt found in `backend/core/llm_prompt.md`.
3. Set the LLM temperature to `0.0` for maximum precision.

## Testing
- **Health Check**: `GET /api/registry` (now on port 8001)
- **Execute Task**: 
  ```bash
  curl -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{"task_id": "get_sales_summary", "parameters": {"start_date": "2024-01-01", "end_date": "2024-03-01"}}'
  ```
