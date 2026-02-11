# Resume Parser POC

This project converts resumes (PDF) into structured JSON data.

## Project Structure

- **`agent.md`**: The authoritative strict contract for the AI agent.
- **`pipeline/`**: Logic for Extraction, Cleaning, Chunking, Parsing.
- **`schemas/`**: Pydantic models defining the output format.
- **`api/`**: FastAPI endpoints.
- **`resume/`**: Data store for uploaded resumes and intermediate JSON artifacts.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configuration:
   Copy `.env.example` to `.env` and set your API keys.

3. Run API:
   ```bash
   uvicorn api.server:app --reload
   ```

## Rules
See `agent.md` for strict development rules.
