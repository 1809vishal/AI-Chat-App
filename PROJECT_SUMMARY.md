# Project Summary: Local AI Assistant with Live Search + RAG

## What this project is
A personal AI chatbot that runs entirely on your own laptop (no cloud
API, no cost) that can:
1. Have a normal conversation, remembering context
2. Search the live internet when a question needs current information
3. Answer questions from your own private documents (e.g. company
   policies) using RAG (Retrieval-Augmented Generation)
4. Automatically decide, per question, which of the above it needs

## Language & tools used

| Tool | What it's for | Why this one |
|---|---|---|
| **Python** | The programming language everything is written in | Standard language for AI/LLM projects, huge ecosystem |
| **Ollama** | Runs the LLM itself, fully on your own machine | Free, no API key, no internet needed after setup |
| **Llama 3.2** (by Meta) | The actual language model that understands and generates text | Small enough to run on low-RAM hardware |
| **nomic-embed-text** | A smaller model that converts text into numerical vectors ("embeddings") | Needed specifically for the RAG/search step, not for chatting |
| **ChromaDB** | A local vector database that stores and searches embeddings | Free, lightweight, no separate server needed |
| **ddgs** (DuckDuckGo Search) | Fetches live web search results | Free, no API key required, unlike Google/Bing search APIs |
| **Streamlit** | Turns the Python script into a browser-based chat UI | Minimal code needed to get a real UI, lightweight |
| **Conda (Miniconda)** | Manages an isolated Python environment | Needed because the system's default Python was outdated |

Everything runs **locally and free** — no subscriptions, no API keys,
no data leaving your machine except for live web searches themselves.

## How it works (architecture, in plain terms)

```
                    ┌─────────────────────┐
   User types  ───► │   Llama 3.2 (LLM)    │
   a question       │   via Ollama         │
                    └──────────┬───────────┘
                               │
                decides: do I need a tool?
                               │
              ┌────────────────┼────────────────┐
              │                                  │
       "needs live info"              "needs company policy"
              │                                  │
              ▼                                  ▼
      ┌───────────────┐               ┌─────────────────────┐
      │  search_web()  │               │ search_company_      │
      │  via ddgs      │               │ policies()            │
      └───────┬────────┘               │ (embeds question →    │
              │                        │  searches ChromaDB)   │
              │                        └──────────┬─────────────┘
              │                                    │
              └──────────────┬─────────────────────┘
                              ▼
                 Results fed back to Llama 3.2
                              │
                              ▼
                   Final answer written and
                   shown in the Streamlit UI
```

## The 7 build steps (in order)

1. **Base model + basic chat** (`chat_basic.py`) — connect to a local
   LLM and keep conversation memory across turns
2. *(same file, combined step)*
3. **Live web search** (`chat_with_tools.py`) — model can call a
   `search_web` tool when it needs current information
4. **Document indexing for RAG** (`rag_setup.py`) — chunks company
   policy documents, converts them to embeddings, stores them in
   ChromaDB (run once, or whenever documents change)
5. **Retrieval + generation** (`rag_chat.py`) — answers questions using
   only the retrieved document chunks as context
6. **Combined router** (`assistant.py`) — one assistant with BOTH
   tools; the model decides which to use per question
7. **Web UI** (`app.py`) — wraps step 6 in a Streamlit browser chat
   interface

## Key concepts to explain to someone else

- **LLMs have no memory between calls** — "memory" is really just
  re-sending the whole conversation history every time.
- **Tool calling** — the model doesn't take actions itself; it asks
  your code to run a function, then reads the result to write its
  answer.
- **Embeddings** — a way of turning text into numbers that capture
  *meaning*, so similar concepts end up as similar numbers, enabling
  search by meaning instead of exact keywords.
- **RAG (Retrieval-Augmented Generation)** — instead of retraining a
  model on your private documents, you retrieve relevant snippets at
  question-time and hand them to the model as context.
- **The model is the router** — rather than writing manual rules for
  "if question contains X, do Y," you describe available tools and let
  the model itself decide which one fits.

## Hardware note
This was built and tested on a laptop with only **3.7GB RAM**, which is
below what's typically recommended for local LLMs. The project uses
small models (Llama 3.2 3B, not larger variants) specifically to fit
that constraint — worth mentioning if explaining this to someone with
better hardware, since they could use larger, more capable models.
