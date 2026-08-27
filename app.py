"""
STEP 8 (CLOUD VERSION): Deployable Web App
------------------------------------------------
Same assistant as app.py, but built to run on Streamlit Community Cloud
instead of your own laptop, so it's reachable from any browser 24/7,
even when your laptop is off.

Two swaps from the local version:
- Chat model: Ollama (local) -> Groq API (free, hosted, fast)
- Embeddings: nomic-embed-text (Ollama) -> sentence-transformers
  (a small model that runs in-process, no separate server needed)

Setup for LOCAL testing before deploying:
    pip install -r requirements.txt
    Create a file: .streamlit/secrets.toml
    Add this line to it:  GROQ_API_KEY = "your-groq-key-here"
    Run:  streamlit run app.py

For deployment instructions, see the DEPLOY.md file in this folder.
"""

import os
import streamlit as st
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb
from ddgs import DDGS

CHAT_MODEL = "openai/gpt-oss-120b"  # larger model = more reliable tool calling than the 20b version
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # small, free, runs in-process
DOCS_FOLDER = "policies"
TOP_K = 2
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

st.set_page_config(page_title="My AI Assistant", page_icon="🤖")

# --- Groq client (reads key from Streamlit secrets, not env vars) ---
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# --- Build the policy index once per app instance, cached ---
@st.cache_resource
def build_policy_index():
    embedder = SentenceTransformer(EMBED_MODEL_NAME)
    chroma_client = chromadb.Client()  # in-memory, rebuilt on each app start
    collection = chroma_client.get_or_create_collection(name="company_policies")

    def chunk_text(text, size, overlap):
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start:start + size].strip())
            start += size - overlap
        return [c for c in chunks if c]

    for filename in os.listdir(DOCS_FOLDER):
        if not filename.endswith(".txt"):
            continue
        with open(os.path.join(DOCS_FOLDER, filename), "r", encoding="utf-8") as f:
            text = f.read()
        for i, chunk in enumerate(chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)):
            embedding = embedder.encode(chunk).tolist()
            collection.upsert(
                ids=[f"{filename}-{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": filename}],
            )

    return embedder, collection


embedder, collection = build_policy_index()


# --- Tool implementations ---
def search_web(query: str) -> str:
    try:
        results = DDGS().text(query, max_results=5)
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    return "\n".join(f"- {r['title']}: {r['body']} (source: {r['href']})" for r in results)


def search_company_policies(query: str) -> str:
    query_embedding = embedder.encode(query).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=TOP_K)
    if not results["documents"][0]:
        return "No relevant company policy found."
    chunks = []
    for text, metadata in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(f"[Source: {metadata['source']}]\n{text}")
    return "\n\n".join(chunks)


available_functions = {
    "search_web": search_web,
    "search_company_policies": search_company_policies,
}

# Groq (OpenAI-compatible) needs explicit JSON-schema tool definitions,
# unlike Ollama which could read them straight from Python docstrings.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the live web for current events, recent news, prices, or anything that could have changed since training.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_company_policies",
            "description": "Search internal company policy documents (leave, remote work, expenses, etc).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The policy question or topic"}},
                "required": ["query"],
            },
        },
    },
]

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are a helpful company assistant with two tools available:\n"
        "1. search_web - for current events, live data, or anything that "
        "could have changed since your training.\n"
        "2. search_company_policies - for questions about internal company "
        "rules, HR policy, leave, expenses, or remote work.\n\n"
        "Use the right tool based on what the question is actually about. "
        "If a question needs neither, answer directly. Never guess at "
        "company policy specifics -- always use search_company_policies."
    ),
}

if "messages" not in st.session_state:
    st.session_state.messages = [SYSTEM_PROMPT]

st.title("🤖 My AI Assistant")
st.caption("Live web search + company policy RAG — hosted, available 24/7")

for msg in st.session_state.messages[1:]:
    if msg["role"] in ("user", "assistant") and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

user_input = st.chat_input("Ask me anything...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            final_text = None

            # --- First call: let the model decide if it needs a tool ---
            try:
                response = groq_client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=st.session_state.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                message = response.choices[0].message
            except Exception:
                # The model failed to generate a valid response/tool call.
                # Retry once WITHOUT tools so the user still gets an answer
                # instead of a crash.
                try:
                    fallback_response = groq_client.chat.completions.create(
                        model=CHAT_MODEL,
                        messages=st.session_state.messages,
                    )
                    final_text = fallback_response.choices[0].message.content
                except Exception:
                    final_text = (
                        "Sorry, I ran into an issue processing that. "
                        "Could you try rephrasing your question?"
                    )
                message = None

            # --- If the first call succeeded, handle tool calls (if any) ---
            if message is not None:
                if message.tool_calls:
                    assistant_msg = {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                    st.session_state.messages.append(assistant_msg)

                    for tool_call in message.tool_calls:
                        func_name = tool_call.function.name
                        import json
                        try:
                            func_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            func_args = {}
                        st.caption(f"🔧 Using tool: {func_name}({func_args})")

                        function_to_call = available_functions.get(func_name)
                        if not function_to_call:
                            result = f"Unknown function: {func_name}"
                        else:
                            query_value = func_args.get("query", "").strip() if isinstance(func_args, dict) else ""

                            if not query_value:
                                # The model's arguments were empty/unusable.
                                # Don't silently search with a blank query --
                                # that returns irrelevant/random results.
                                result = (
                                    "No usable search query was provided by the model "
                                    "for this request."
                                )
                            else:
                                try:
                                    result = function_to_call(query_value)
                                except Exception as e:
                                    result = f"Tool execution failed: {e}"

                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": result,
                        })

                    # --- Second call: model writes the final answer ---
                    try:
                        final_response = groq_client.chat.completions.create(
                            model=CHAT_MODEL,
                            messages=st.session_state.messages,
                        )
                        final_text = final_response.choices[0].message.content
                    except Exception:
                        # The model failed to summarize the tool results.
                        # Show the raw results directly rather than crashing.
                        last_tool_result = st.session_state.messages[-1]["content"]
                        final_text = (
                            "I ran into trouble putting together a clean answer. "
                            f"Here's what I found:\n\n{last_tool_result}"
                        )
                else:
                    final_text = message.content

            st.markdown(final_text)
            st.session_state.messages.append({"role": "assistant", "content": final_text})
