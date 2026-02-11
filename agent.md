# 🧠 Resume Parser POC — Agent Creation & Execution Rules

## 0. Purpose
This file defines **how an AI agent must create, modify, and reason about this project**.
It acts as a **strict contract** between the human (project owner) and any agent.

This project is a **POC-first, correctness-first resume parser**.

---

## 1. Project Goal (Non‑Negotiable)

This project converts resumes into **fully structured, schema-valid JSON**.

**Primary Workflow:**
```
PDF Resume (1–200 pages)
→ Cleaned text
→ Semantic blocks
→ Semantic Chunks
→ (Optional) Vectors & RAG Retrieval
→ Structured JSON
```

This project is **NOT**:
- a chatbot
- a search engine
- an autonomous agent system

**Priorities:**
1. **Correctness**
2. **Explainability**
3. **Debuggability**
4. **POC Clarity** over optimization

---

## 2. Agent Operating Rules

### Allowed
- Read files
- Explain architecture
- Propose changes
- Generate code **only after explicit approval**

### Strictly Forbidden
- Deleting files without permission
- Renaming files/folders without permission
- **Using LangChain Agents** (e.g., `AgentExecutor`, `Tool` use)
- Making assumptions about user intent
- Creating hidden/opaque logic chains

If unsure → **STOP and ASK**.

---

## 3. Technology Stack (Mandatory)

### Core
- **Python 3.10+**

### Libraries (requirements.txt concept)
- `langchain` / `langchain-community` (Strictly as a utility library)
- `pymupdf` (PDF text extraction)
- `fastapi` (API handling)
- `pydantic` (Schema validation & serialization, output parsing)
- `httpx` / `requests` (API calls)
- `numpy` (For embeddings)
- `faiss-cpu` / `chromadb` (Vector Store - Local only)
- `openai` / `anthropic` (LLM Clients)
- `python-dotenv` (Configuration Management)

### Binary Dependencies (System Level)
- **Poppler Utils**: Required for PDF processing if PyMuPDF fails.

### MCP / Tooling Policy
- Point **ONLY** to official documentation for any external tools.
- Do NOT invent APIs or assume "agent magic".
- All references must be directional (e.g., "Use the `browser_action` tool"), not hard code dependencies.

---

## 4. LangChain Policy (Strict Utility Usage)

**LangChain IS ALLOWED**, but **ONLY** as a low-level utility library. It must **NOT** make decisions or run loops.

### ✅ Allowed LangChain Usage
- **TextSplitter**: Use `RecursiveCharacterTextSplitter` for chunking.
- **PromptTemplate**: Use for managing System and User prompts.
- **LLM Wrappers**: Use `ChatOpenAI`, `ChatAnthropic` for consistent API calls.
- **OutputParsers**: Use `PydanticOutputParser` for structure enforcement.
- **Embeddings**: Use standard embedding model wrappers (e.g., `OpenAIEmbeddings`).
- **VectorStore**: Use standard vector store abstractions (e.g., `FAISS`).

### ❌ Forbidden LangChain Usage
- **Agents**: NO `AgentExecutor`, NO autonomous loops.
- **Tools**: LLMs must NOT decide which tools to call. The pipeline is hard-coded in Python.
- **Memory**: Do NOT use conversational memory buffers. This is a stateless pipeline.
- **RetrievalQA**: Do NOT use pre-built RAG chains. Implement the retrieval logic explicit in `retriever.py`.

**Principle:** LangChain is a helper library, not the architect.

---

## 5. Folder & File Architecture (Locked)

The system uses a **UUID-based storage** approach for traceability.

```
resume_parser/
├── resume/
│   └── {resume_uuid}/
│       ├── original.pdf
│       ├── extracted_text.json    (Schema Defined Below)
│       ├── clean_text.json        (Schema Defined Below)
│       ├── semantic_blocks.json   (Schema Defined Below)
│       ├── chunks.json            (Schema Defined Below)
│       ├── embeddings/            (Local Vector Store Index)
│       ├── logs/                  (Processing Logs)
│       └── final_resume.json      (Final Schema)
├── pipeline/
│   ├── text_extractor.py
│   ├── text_cleaner.py
│   ├── semantic_blocker.py
│   ├── chunker.py             (Uses LangChain TextSplitter)
│   ├── embedder.py            (Handles Embeddings & Vector Store Creation)
│   ├── retriever.py           (Handles Similarity Search)
│   ├── llm_parser.py          (Uses LangChain LLM + Prompts)
│   └── validator.py
├── api/
│   └── server.py              (FastAPI Entry Point)
├── config/
│   └── settings.py            (Centralized Configuration & Constants)
├── prompts/                   (Centralized Prompt Management)
│   ├── system_prompts.yaml    (Persona & Strict Rules)
│   └── extraction_templates.py (Task-Specific Templates)
├── schemas/
│   └── resume_schema.py
├── tests/
├── main_pipeline.py
├── requirements.txt
├── Dockerfile                 (System Dependencies & Environment)
└── agent.md
```

**Rules:**
- **Reflect the Real World**: Files must exist where stated.
- **One Responsibility Per File**: Do not merge stages.
- **Traceability**: Every stage produces a JSON artifact in the `{resume_uuid}` folder.

---

## 6. Pipeline Components (Mandatory Documentation)

The agent must understand and respect these **8 distinct stages**:

### 1. Text Extraction
- **Input:** `original.pdf`
- **Output:** `extracted_text.json`
- **Tooling:** PyMuPDF.
- **Constraint:** **NO LLMs**. Raw extraction only.

### 2. Text Cleaning
- **Input:** `extracted_text.json`
- **Output:** `clean_text.json`
- **Logic:** Noise removal, whitespace normalization.

### 3. Semantic Block Creation
- **Input:** `clean_text.json`
- **Output:** `semantic_blocks.json`
- **Logic:** Group text by **meaning**, NOT by page.
- **Constraint:** Heuristic/Layout analysis required.

### 4. Chunking Strategy (Mandatory)
- **Input:** `semantic_blocks.json`
- **Output:** `chunks.json`
- **Logic:**
    - **Tooling:** Use `LangChain TextSplitter` (configured in `config/settings.py`).
    - **Token-aware:** Respect context limits.
    - **Section-preserving:** Do not split logical sections mid-sentence.

### 5. Embedding & Vector Storage (Optional)
- **Input:** `chunks.json`
- **Output:** `embeddings/` (FAISS Index on disk)
- **File:** `pipeline/embedder.py`
- **Constraint:** **Optional Stage**. If not enabled, `llm_parser.py` consumes chunks directly.
- **Logic:**
    - Initialize Embedding Model (LangChain `Embeddings`).
    - Batch process chunks into vectors.
    - Store in FAISS/Chroma.

### 6. Retrieval (RAG Logic - System Only)
- **Input:** **System-Generated Intent** (e.g., "Extract Education"), NOT User Queries.
- **Output:** Relevant Chunks
- **File:** `pipeline/retriever.py`
- **Tooling:** LangChain `VectorStoreRetriever`.
- **Constraint:** This is NOT a Q&A chatbot. Queries are hard-coded extraction tasks.

### 7. LLM Parsing
- **Input:** Retrieved Chunks (or All Chunks) + Prompts
- **Output:** Structured fields.
- **File:** `pipeline/llm_parser.py`
- **Logic:**
    - **Tooling:** Use `LangChain LLM Wrapper`.
    - **Prompt Source:** Load from `prompts/` directory. **Prompts are treated as Source Code.** Changes must be versioned.
    - **Strict JSON:** Enforce schema via `Pydantic` or `OutputParsers`.

### 8. Validation
- **Input:** LLM Output JSON
- **Output:** Validated `final_resume.json`
- **File:** `pipeline/validator.py`
- **Logic:** Pydantic validation. Reject hallucinations.

---

## 7. Change Approval Protocol

Before making **ANY** change to code or architecture, the agent must:

1.  **Explain** what will change (referencing specific files).
2.  **Explain why** it is necessary (linking to the goal).
3.  **Wait for explicit approval**.
4.  **Confirm Schema Lock:** Field names (e.g., `work_experience`) must NOT change without explicit approval.

Without approval → **DO NOTHING**.

---

## 8. Data Contracts (JSON Schemas)

Every stage MUST produce JSON adhering to these strict keys to ensuring compatibility.

### 1. `extracted_text.json`
```json
{
  "pages": [
    {
      "page_number": 1,
      "text": "Raw extracted text...",
      "origin": "pymupdf"
    }
  ],
  "metadata": { "total_pages": 5 }
}
```

### 2. `clean_text.json`
```json
{
  "content": "Full normalized text joined from pages...",
  "cleaning_log": ["Removed 3 headers", "Fixed bullet points"]
}
```

### 3. `semantic_blocks.json`
```json
[
  {
    "id": "block_001",
    "category": "Experience", // or "Education", "Skills", "Header"
    "raw_text": "Software Engineer at Google...",
    "page_span": [1, 2]
  }
]
```

---

## 9. Error Handling Strategy

1. **Partial Failures:** If one semantic block fails LLM parsing, store it as `{"error": "parsing_failed", "raw_text": "..."}` in the final JSON. DO NOT crash the entire process.
2. **Logging:** Every script must log to `pipeline.log` in the `{resume_uuid}/logs/` directory.

---

## 10. Quality Bar

- **Language:** Simple, clear, non-academic.
- **Assumptions:** None. Verify everything.
- **Optimization:** Secondary to correctness. Code must be understandable by a junior engineer.
- **Debuggability:** Every stage saves its intermediate JSON output.
- **Determinism:** Given the same PDF and config, output JSON keys must be identical across runs.

---
## END OF FILE
