# LegalMind Agent Code Explanation

This file explains how the project works step by step, from the configuration layer to the user interface. The code is organized as a small legal assistant system built with FastAPI, ChromaDB, Gradio, and an LLM provider through `backend/app/llm/groq.py`.

## 1. Project Idea

LegalMind Agent is a legal assistant for Tunisian law. The goal of the project is to let a user:

1. Ask a legal question in natural language.
2. Search the indexed Tunisian legal PDFs.
3. Receive an answer with citations.
4. Upload a document and run a simple legal analysis on it.

The application is split into two main parts:

- A FastAPI backend that does ingestion, retrieval, chat, and agent analysis.
- A Gradio frontend that gives the user a simple browser interface.

## 2. Configuration Layer

The first important file is `backend/app/config.py`.

This file loads environment variables from `.env` and stores them in the `settings` object. It is the central place where the app reads runtime values such as:

- `LLM_PROVIDER`
- `GROQ_API_KEY`
- `GROQ_CHAT_MODEL`
- `SOURCES_DIR`
- `CHROMA_DIR`
- `UPLOADS_DIR`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `TOP_K`
- `API_HOST`
- `API_PORT`

Why this matters:

- It keeps the rest of the code clean.
- It avoids hardcoding paths and secrets in many files.
- It makes the project easier to configure for local development.

## 3. API Entry Point

The main backend application is in `backend/app/main.py`.

This file creates the FastAPI app and exposes the HTTP routes used by the frontend and by manual testing.

### `/health`

Returns a simple status object so you can quickly check if the backend is alive.

### `/`

Returns a small API welcome message with links to docs and health.

### `/ingest`

This route reads the PDF files in the sources folder and indexes them into ChromaDB.

### `/chat`

This is the main conversational endpoint. It:

1. Reads the user session history.
2. Searches the legal database.
3. Builds a prompt with the retrieved context.
4. Sends the prompt to the LLM.
5. Stores the new conversation turn in memory.
6. Returns the answer plus citations.

### `/agent/analyze`

This route runs the more advanced agent flow. It can combine legal search with uploaded document analysis.

### `/uploads`

This route stores uploaded files on disk and returns a document ID that can be reused later.

## 4. Data Ingestion Flow

The ingestion pipeline starts in `backend/app/ingest/loader.py`.

This file is responsible for reading PDF files from the `sources` folder. For each PDF it:

1. Opens the file with `PdfReader` from `pypdf`.
2. Extracts text page by page.
3. Keeps the page number so citations can later point to the right location.
4. Splits the page text into chunks.
5. Saves the chunks and metadata into ChromaDB.

The loader also removes stale sources that are no longer present in the folder.

### Why page-based extraction matters

The project is meant to provide legal citations. That means the app must know which page a passage came from. Without page tracking, the answer would be less trustworthy and harder to verify.

## 5. Text Chunking

The chunking logic is in `backend/app/ingest/chunker.py`.

This file takes a long text and splits it into smaller overlapping chunks. The overlap helps preserve context between neighboring chunks.

The process is simple:

1. Clean repeated whitespace.
2. Read a slice of the text with the configured `chunk_size`.
3. Move forward, but keep a small overlap defined by `chunk_overlap`.
4. Repeat until the full text is covered.

Why this matters:

- Large legal documents are easier to search when broken into smaller parts.
- Overlap reduces the chance of cutting a legal idea in half.

## 6. Vector Store

The ChromaDB setup is in `backend/app/vectorstore/chroma.py`.

This file creates a persistent Chroma client and a collection named `tunisian_law_chroma`.

What it does:

- Stores embeddings on disk in the configured Chroma directory.
- Reuses the same collection across requests.
- Provides the retrieval backend for legal search.

This is the database layer for semantic search. Instead of looking for exact keywords only, the app can search by meaning.

## 7. Retrieval Layer

The retrieval logic is in `backend/app/rag/retriever.py`.

This file defines the `search()` function.

The flow is:

1. Receive the user query.
2. Ask ChromaDB for the nearest documents.
3. Return the matching text chunks and their metadata.

The metadata includes fields like:

- `source`
- `page`
- `chunk_id`

This is what later becomes the citation list shown to the user.

## 8. RAG Answer Generation

The answer-building logic is in `backend/app/rag/qa.py`.

This file is where retrieval augmented generation actually happens.

### Step-by-step flow

1. The user question is received.
2. The retriever finds the most relevant legal chunks.
3. `_build_prompt()` creates a chat prompt.
4. The prompt includes:
   - a system instruction in Arabic
   - the retrieved legal passages
   - recent conversation history
   - the current user question
5. The prompt is sent to the LLM through `chat_completion()`.
6. The returned text becomes the final answer.
7. The retrieved chunks are converted into `SourceCitation` objects.

The system prompt asks the model to:

- answer in Arabic,
- be professional and clear,
- mention references with page numbers,
- ask for clarification if the context is not enough.

This is the core of the legal chat experience.

## 9. LLM Provider Layer

The file `backend/app/llm/groq.py` is the gateway to the language model.

It does three important jobs:

1. Checks that the selected provider is Groq.
2. Sends the request to the Groq chat completions endpoint.
3. Returns a fallback message if the key is missing or the request fails.

### Main function

`chat_completion(messages, temperature=0.2)` takes a list of chat messages and returns plain text.

### Success path

If the API call works:

- the request body includes the model name,
- the message list,
- the temperature,
- the API key in the authorization header.

### Failure path

If something goes wrong, `_fallback_chat()` returns a local Arabic response that explains the limitation and suggests what to check.

This fallback is useful because it prevents the whole app from crashing if the LLM provider is unavailable.

## 10. Conversation Memory

The memory layer is in `backend/app/memory/conversation.py`.

This file implements a very small in-memory store keyed by `session_id`.

It supports two operations:

- `get(session_id)` to retrieve previous messages.
- `append(session_id, role, content)` to save a new turn.

This memory is not permanent database storage. It exists only while the server is running.

Why it matters:

- It lets the assistant keep short conversational context.
- It improves the quality of follow-up answers.

## 11. Contract Analysis Tool

The document analysis logic is in `backend/app/agent/tools/contract_analyzer.py`.

This tool lets the user upload a PDF, DOCX, or text file and then analyze it.

### `save_upload(file)`

This function saves the uploaded file into the uploads folder and returns a generated document ID.

### `_extract_text(path)`

This helper reads text from:

- PDF files with `PdfReader`
- DOCX files with `python-docx`
- plain text files with standard file reading

### `analyze_contract(document_id)`

This function:

1. Finds the uploaded file.
2. Extracts and compacts the text.
3. Searches for simple legal risk patterns.
4. Builds a short summary.
5. Returns notes about possible contract issues.

The current analysis is rule-based. It is not a full legal expert system, but it gives a useful first review.

## 12. Legal Search Tool

The file `backend/app/agent/tools/legal_rag.py` defines a reusable legal search tool.

It:

1. Searches the vector store for relevant legal passages.
2. Builds a prompt that includes only the retrieved text.
3. Sends the prompt to the LLM.
4. Returns the answer plus citations.

This tool is used by the higher-level agent planner when the user asks a legal question.

## 13. Agent Planner

The orchestration logic is in `backend/app/agent/planner.py`.

This file makes the system behave like a small agent instead of a single chat model.

### `_plan_steps(user_query)`

This helper asks the LLM to produce a short plan of 3 to 5 steps in Arabic.

### `run_agent(message, history, document_id)`

This is the full agent workflow.

It does the following:

1. Creates a short plan.
2. If a document ID is provided, it analyzes the uploaded document.
3. Runs the legal search tool on the user message.
4. Combines the legal results and document analysis into one synthesis prompt.
5. Calls the LLM again to produce the final response.
6. Returns the plan, answer, citations, and notes.

This is the part that gives the project its multi-step behavior.

## 14. Request and Response Models

The schema definitions are in `backend/app/models/schemas.py`.

These Pydantic models describe the structure of the API data.

Important models:

- `ChatRequest`
- `ChatResponse`
- `AgentRequest`
- `AgentResponse`
- `SourceCitation`

Why they matter:

- They validate incoming requests.
- They make the API output predictable.
- They keep the frontend and backend in sync.

## 15. Frontend UI

The Gradio interface is in `frontend/app.py`.

This is the part the user sees in the browser.

### Legal chat tab

The user enters:

- a session ID
- a legal question

The UI sends the request to `/chat` and displays:

- the answer
- the list of sources

### Contract analysis tab

The user can:

1. Upload a document.
2. Receive a document ID.
3. Ask for analysis.
4. Get a plan, result, notes, and citations.

The frontend is intentionally simple. Its role is to pass user input to the backend and show the result clearly.

## 16. End-to-End Flow

Here is the full path of a legal question:

1. The user types a question in Gradio.
2. Gradio sends the question to FastAPI `/chat`.
3. The backend loads the conversation history.
4. The retriever searches ChromaDB for relevant legal passages.
5. The QA layer builds a prompt with context and history.
6. The LLM generates the final answer.
7. The backend stores the conversation turn.
8. The frontend shows the answer and citations.

Here is the full path of a document analysis request:

1. The user uploads a file.
2. The backend stores it in `uploads`.
3. The agent receives the document ID.
4. The tool extracts the text and checks for risk patterns.
5. The legal search tool adds legal context.
6. The planner asks the LLM to synthesize everything.
7. The UI displays the result.

## 17. What Each Folder Means

- `backend/` contains the application logic.
- `frontend/` contains the user interface.
- `sources/` contains the Tunisian legal PDFs.
- `data/` contains the persistent vector database.
- `uploads/` contains user files.
- `scripts/` contains utility scripts such as ingestion.

## 18. Full Summary

LegalMind Agent is a small legal AI system that combines document ingestion, semantic search, retrieval augmented generation, session memory, and a two-tool agent flow.

The project works in this order:

1. It loads legal PDF files from the sources folder.
2. It splits them into overlapping chunks.
3. It stores those chunks in ChromaDB.
4. It searches the most relevant legal passages when the user asks a question.
5. It sends the question and retrieved context to the LLM.
6. It returns an Arabic answer with citations.
7. It can also analyze uploaded contracts and produce notes about possible risks.
8. The Gradio UI gives the user a simple way to use everything from the browser.

The architecture is intentionally modular, which makes it easy to understand, test, and extend.

In short, the project turns Tunisian legal documents into a searchable assistant that can answer questions and inspect documents step by step.