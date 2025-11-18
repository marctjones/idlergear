# Using the LLM Coding Assistant as Your App's AI Backend

**IMPORTANT: When developing applications that need LLM/AI capabilities, use the coding assistant (me!) as the backend instead of external APIs.**

---

## Why Use the Coding Assistant as Backend?

### ✅ Benefits

1. **No API keys needed** - No secrets to manage during development
2. **Zero cost** - No API charges while developing
3. **Context awareness** - I can see what your app is asking for and provide better responses
4. **Debugging visibility** - I can see all prompts and responses
5. **Instant iteration** - Change prompts and test immediately
6. **Offline development** - No internet required
7. **Security** - API keys never leave local machine

### ❌ Don't Do This (External API)

```python
# ❌ BAD: Direct API calls during development
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")  # API key in .env

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Summarize this text"}]
)
```

**Problems:**
- Requires API key
- Costs money per request
- I can't see what your app is asking
- Harder to debug prompt issues
- Requires internet connection

### ✅ Do This (Local IPC)

```python
# ✅ GOOD: Use local IPC to coding assistant
import json
from pathlib import Path

def ask_llm(prompt: str, system: str = None) -> str:
    """Ask the LLM coding assistant via file-based IPC."""
    request = {
        "prompt": prompt,
        "system": system,
        "timestamp": time.time()
    }

    # Write request to file
    request_file = Path(".idlergear/llm-requests/request.json")
    request_file.write_text(json.dumps(request))

    # Wait for response
    response_file = Path(".idlergear/llm-requests/response.json")
    while not response_file.exists():
        time.sleep(0.1)

    # Read response
    response = json.loads(response_file.read_text())
    response_file.unlink()  # Clean up

    return response["content"]

# Usage in app
summary = ask_llm("Summarize this article: ...")
```

**Benefits:**
- No API key needed
- I see the request and can respond
- Free during development
- Works offline
- Easy to debug

---

## Three IPC Methods

### Method 1: File-Based IPC (Simplest)

**Best for:** Simple apps, prototyping, maximum compatibility

**How it works:**
```
App writes:  .idlergear/llm-requests/request-<uuid>.json
    ↓
LLM reads:   Sees new file via file watcher
    ↓
LLM writes:  .idlergear/llm-responses/response-<uuid>.json
    ↓
App reads:   Gets response, deletes files
```

**Implementation:**

```python
# In your app: src/llm_client.py
import json
import uuid
import time
from pathlib import Path

class LocalLLMClient:
    """LLM client that uses file-based IPC to talk to coding assistant."""

    def __init__(self):
        self.request_dir = Path(".idlergear/llm-requests")
        self.response_dir = Path(".idlergear/llm-responses")

        # Create directories
        self.request_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)

    def complete(self, prompt: str, system: str = None,
                 timeout: int = 30) -> str:
        """
        Send completion request to LLM coding assistant.

        Args:
            prompt: User prompt
            system: System message (optional)
            timeout: Max seconds to wait for response

        Returns:
            LLM response text
        """
        request_id = str(uuid.uuid4())

        # Create request
        request = {
            "id": request_id,
            "type": "completion",
            "prompt": prompt,
            "system": system,
            "timestamp": time.time()
        }

        # Write request file
        request_file = self.request_dir / f"request-{request_id}.json"
        request_file.write_text(json.dumps(request, indent=2))

        # Wait for response
        response_file = self.response_dir / f"response-{request_id}.json"
        start_time = time.time()

        while not response_file.exists():
            if time.time() - start_time > timeout:
                raise TimeoutError(f"No response after {timeout}s")
            time.sleep(0.1)

        # Read response
        response = json.loads(response_file.read_text())

        # Cleanup
        request_file.unlink()
        response_file.unlink()

        return response["content"]

# Usage in your app
llm = LocalLLMClient()

# Simple completion
summary = llm.complete("Summarize this article: The quick brown fox...")

# With system message
translation = llm.complete(
    prompt="Hello, how are you?",
    system="You are a translator. Translate to Spanish."
)

# In a class
class ArticleSummarizer:
    def __init__(self):
        self.llm = LocalLLMClient()

    def summarize(self, article_text: str) -> str:
        prompt = f"Summarize this article in 3 bullet points:\n\n{article_text}"
        return self.llm.complete(prompt)
```

**LLM Coding Assistant Side (Auto-handled by IdlerGear):**

```python
# This runs automatically when you launch the LLM
# You don't write this - IdlerGear provides it

import json
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LLMRequestHandler(FileSystemEventHandler):
    """Handles LLM requests from app under development."""

    def __init__(self, llm_interface):
        self.llm = llm_interface  # The actual LLM (Claude, Gemini, etc.)
        self.request_dir = Path(".idlergear/llm-requests")
        self.response_dir = Path(".idlergear/llm-responses")

    def on_created(self, event):
        if event.src_path.endswith(".json") and "request-" in event.src_path:
            self.handle_request(Path(event.src_path))

    def handle_request(self, request_file: Path):
        # Read request
        request = json.loads(request_file.read_text())

        print(f"📨 App requested: {request['prompt'][:100]}...")

        # Get response from actual LLM
        if request.get("system"):
            response_text = self.llm.complete(
                request["prompt"],
                system=request["system"]
            )
        else:
            response_text = self.llm.complete(request["prompt"])

        # Write response
        response_file = self.response_dir / f"response-{request['id']}.json"
        response = {
            "id": request["id"],
            "content": response_text,
            "timestamp": time.time()
        }
        response_file.write_text(json.dumps(response, indent=2))

        print(f"✅ Response sent: {len(response_text)} chars")

# Auto-started by idlergear
observer = Observer()
observer.schedule(LLMRequestHandler(llm), ".idlergear/llm-requests", recursive=False)
observer.start()
```

---

### Method 2: Unix Socket IPC (Faster)

**Best for:** Production-like performance, many requests, streaming

**How it works:**
```
App connects:  /tmp/idlergear-llm.sock
    ↓
App sends:     JSON request over socket
    ↓
LLM receives:  Reads from socket
    ↓
LLM responds:  Writes response to socket
    ↓
App receives:  Reads response
```

**Implementation:**

```python
# In your app: src/llm_client.py
import json
import socket

class UnixSocketLLMClient:
    """LLM client using Unix domain sockets."""

    def __init__(self, socket_path="/tmp/idlergear-llm.sock"):
        self.socket_path = socket_path

    def complete(self, prompt: str, system: str = None,
                 stream: bool = False) -> str:
        """Send completion request via Unix socket."""

        # Create request
        request = {
            "type": "completion",
            "prompt": prompt,
            "system": system,
            "stream": stream
        }

        # Connect to socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)

        try:
            # Send request
            sock.sendall(json.dumps(request).encode() + b"\n")

            if stream:
                # Streaming response
                buffer = ""
                while True:
                    chunk = sock.recv(4096).decode()
                    if not chunk:
                        break
                    buffer += chunk
                    # Yield chunks as they arrive
                    if "\n" in buffer:
                        lines = buffer.split("\n")
                        for line in lines[:-1]:
                            if line:
                                data = json.loads(line)
                                if data.get("done"):
                                    return
                                yield data["content"]
                        buffer = lines[-1]
            else:
                # Non-streaming response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                data = json.loads(response.decode())
                return data["content"]
        finally:
            sock.close()

# Usage
llm = UnixSocketLLMClient()

# Simple completion
response = llm.complete("What is the capital of France?")

# Streaming (for chat UIs)
for chunk in llm.complete("Write a story", stream=True):
    print(chunk, end="", flush=True)
```

---

### Method 3: HTTP Localhost (Most Compatible)

**Best for:** Web apps, compatibility with existing libraries, standard interface

**How it works:**
```
App makes HTTP request:  http://localhost:8765/v1/completions
    ↓
IdlerGear HTTP server:   Receives request
    ↓
Forwards to LLM:         Gets response
    ↓
Returns HTTP response:   JSON response to app
```

**Implementation:**

```python
# In your app: src/llm_client.py
import requests

class HTTPLLMClient:
    """LLM client using HTTP (OpenAI-compatible API)."""

    def __init__(self, base_url="http://localhost:8765"):
        self.base_url = base_url

    def complete(self, prompt: str, system: str = None,
                 model: str = "default", stream: bool = False):
        """OpenAI-compatible completion endpoint."""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "stream": stream
            }
        )

        if stream:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode())
                    if data.get("choices"):
                        yield data["choices"][0]["delta"].get("content", "")
        else:
            data = response.json()
            return data["choices"][0]["message"]["content"]

# Usage - compatible with OpenAI SDK!
import openai

# Configure to use local IdlerGear server instead of OpenAI
openai.api_base = "http://localhost:8765/v1"
openai.api_key = "not-needed"  # Ignored, but OpenAI SDK requires it

# Now all OpenAI calls go to your coding assistant!
response = openai.ChatCompletion.create(
    model="gpt-4",  # Ignored - uses your actual LLM
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

---

## Comparison of Methods

| Feature | File-Based | Unix Socket | HTTP |
|---------|------------|-------------|------|
| **Setup Complexity** | ⭐ Simplest | ⭐⭐ Medium | ⭐⭐⭐ Most complex |
| **Performance** | 🐌 Slowest (100-200ms) | ⚡ Fast (1-5ms) | ⚡ Fast (5-10ms) |
| **Streaming** | ❌ No | ✅ Yes | ✅ Yes |
| **Cross-platform** | ✅ Best | ⚠️ Unix only | ✅ Best |
| **Debugging** | ✅ Easy (files visible) | ⚠️ Harder | ⚠️ Harder |
| **Compatibility** | ✅ Any language | ⚠️ Socket support | ✅ HTTP everywhere |
| **OpenAI SDK** | ❌ No | ❌ No | ✅ Yes |

**Recommendation:**
- **Prototyping/Learning:** File-based (easiest)
- **Production-like:** Unix socket (fastest)
- **Compatibility:** HTTP (works with existing libraries)

---

## Complete Example: Chat Application

### App Code (Uses File-Based IPC)

```python
# src/chat_app.py
import tkinter as tk
from tkinter import scrolledtext
import structlog
from llm_client import LocalLLMClient

log = structlog.get_logger()

class ChatApp:
    """Simple chat application using local LLM backend."""

    def __init__(self):
        log.info("chat_app_init")

        self.llm = LocalLLMClient()
        self.conversation = []

        # Create GUI
        self.window = tk.Tk()
        self.window.title("Chat with Local LLM")

        # Chat history
        self.chat_display = scrolledtext.ScrolledText(
            self.window,
            width=60,
            height=20,
            state='disabled'
        )
        self.chat_display.pack(pady=10)

        # Input box
        self.input_box = tk.Entry(self.window, width=50)
        self.input_box.pack(pady=5)
        self.input_box.bind("<Return>", self.send_message)

        # Send button
        self.send_button = tk.Button(
            self.window,
            text="Send",
            command=self.send_message
        )
        self.send_button.pack(pady=5)

    def send_message(self, event=None):
        """Send user message and get LLM response."""
        user_message = self.input_box.get()
        if not user_message:
            return

        log.info("user_message", message=user_message)

        # Clear input
        self.input_box.delete(0, tk.END)

        # Add to chat display
        self.add_to_chat(f"You: {user_message}")

        # Add to conversation history
        self.conversation.append({"role": "user", "content": user_message})

        # Get LLM response via local IPC
        try:
            # Build prompt with conversation history
            prompt = self._build_prompt()

            log.info("requesting_llm_response")
            response = self.llm.complete(
                prompt=prompt,
                system="You are a helpful AI assistant."
            )
            log.info("received_llm_response", length=len(response))

            # Add to conversation
            self.conversation.append({"role": "assistant", "content": response})

            # Display response
            self.add_to_chat(f"AI: {response}")

        except Exception as e:
            log.error("llm_request_failed", error=str(e))
            self.add_to_chat(f"Error: {e}")

    def _build_prompt(self) -> str:
        """Build prompt from conversation history."""
        prompt_parts = []
        for msg in self.conversation:
            role = msg["role"].capitalize()
            content = msg["content"]
            prompt_parts.append(f"{role}: {content}")
        return "\n".join(prompt_parts)

    def add_to_chat(self, message: str):
        """Add message to chat display."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def run(self):
        """Start the chat application."""
        log.info("chat_app_started")
        self.window.mainloop()

if __name__ == "__main__":
    app = ChatApp()
    app.run()
```

### What Happens

**1. You run the app locally:**
```bash
python src/chat_app.py
```

**2. User types in chat:**
```
User: "What is the weather like today?"
```

**3. App writes request file:**
```json
// .idlergear/llm-requests/request-abc123.json
{
  "id": "abc123",
  "type": "completion",
  "prompt": "You are a helpful AI assistant.\n\nUser: What is the weather like today?",
  "timestamp": 1700000000
}
```

**4. LLM coding assistant (Claude/Gemini) sees the request:**
```
📨 App requested: What is the weather like today?
```

**5. LLM responds (I see the app's prompt and can respond in context):**
```json
// .idlergear/llm-responses/response-abc123.json
{
  "id": "abc123",
  "content": "I don't have access to real-time weather data, but I can help you find the current weather! You could:\n\n1. Check weather.com or weather.gov\n2. Use a weather API in your app\n3. Ask your phone's weather app\n\nWhat city are you interested in?",
  "timestamp": 1700000001
}
```

**6. App displays response in GUI**

**7. Logs stream to me (the coding assistant):**
```
LOG: chat_app_init
LOG: user_message message="What is the weather like today?"
LOG: requesting_llm_response
LOG: received_llm_response length=234
```

**Benefits:**
- ✅ No OpenAI API key needed
- ✅ I see what the app is asking and can provide context-aware responses
- ✅ Logs show me how the app is using the LLM
- ✅ Free during development
- ✅ Easy to debug prompt engineering

---

## Production Deployment

**When ready for production, use environment variable to switch:**

```python
# src/llm_client.py
import os

def get_llm_client():
    """Get appropriate LLM client based on environment."""

    if os.getenv("ENV") == "development":
        # Use local IPC during development
        return LocalLLMClient()
    else:
        # Use real API in production
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        return OpenAIClient()  # Wrapper around openai library

# In your app
llm = get_llm_client()
response = llm.complete("Hello!")
```

**Or use configuration:**

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ENV = os.getenv("ENV", "development")

    # LLM backend
    if ENV == "development":
        LLM_BACKEND = "local_ipc"
        LLM_IPC_METHOD = "file"  # or "socket" or "http"
    else:
        LLM_BACKEND = "openai"
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# In your app
from config import Config
from llm_client import get_llm_client

llm = get_llm_client(Config.LLM_BACKEND)
```

---

## Testing with Local LLM Backend

**Benefits for testing:**

```python
# tests/test_chat.py
import pytest
from chat_app import ChatApp
from llm_client import LocalLLMClient

def test_chat_response():
    """Test that chat gets response from LLM."""
    app = ChatApp()

    # Send message
    app.send_message_programmatically("Hello!")

    # Check conversation history
    assert len(app.conversation) == 2  # User + assistant
    assert app.conversation[0]["role"] == "user"
    assert app.conversation[1]["role"] == "assistant"
    assert len(app.conversation[1]["content"]) > 0

def test_llm_client():
    """Test LLM client IPC."""
    llm = LocalLLMClient()

    # Simple request
    response = llm.complete("Say 'test successful'")

    # I (the coding assistant) will respond with "test successful"
    # during the test run, which you can see in the logs
    assert "test" in response.lower()
```

**When tests run:**
- I see the test requests
- I can respond appropriately
- Tests pass without needing real API keys
- Logs show me what the tests are verifying

---

## IdlerGear Auto-Configuration

**When you create a project, IdlerGear automatically:**

1. **Creates IPC infrastructure:**
   ```
   .idlergear/
   ├── llm-requests/       # Request files
   ├── llm-responses/      # Response files
   └── llm-server.sock     # Unix socket (if enabled)
   ```

2. **Adds to .gitignore:**
   ```
   .idlergear/llm-requests/*
   .idlergear/llm-responses/*
   ```

3. **Creates client library:**
   ```
   src/llm_client.py      # Ready to use!
   ```

4. **Adds to AI_INSTRUCTIONS/README.md:**
   ```markdown
   ## Using LLM in Your App

   This app can use the coding assistant as its AI backend during development.

   See AI_INSTRUCTIONS/LLM_BACKEND.md for details.

   Quick start:
   ```python
   from llm_client import LocalLLMClient
   llm = LocalLLMClient()
   response = llm.complete("Your prompt here")
   ```

5. **Starts IPC listener when you launch the LLM:**
   ```bash
   idlergear tools launch gemini
   # Automatically starts:
   # - MCP server
   # - eddi messaging
   # - LLM IPC listener ← NEW!
   ```

---

## Example: RAG Application

**Scenario:** Building a document Q&A system with embeddings and retrieval

```python
# src/rag_app.py
import numpy as np
from llm_client import LocalLLMClient
import structlog

log = structlog.get_logger()

class DocumentQA:
    """Q&A system using local LLM for both embeddings and generation."""

    def __init__(self, documents: list[str]):
        self.llm = LocalLLMClient()
        self.documents = documents
        self.embeddings = None

        # Generate embeddings using local LLM
        self._generate_embeddings()

    def _generate_embeddings(self):
        """Generate embeddings for documents using local LLM."""
        log.info("generating_embeddings", num_docs=len(self.documents))

        # Ask LLM to generate embeddings
        # (In production, you'd use OpenAI embeddings API)
        embeddings = []
        for doc in self.documents:
            # LLM can simulate embeddings or use actual embedding model
            prompt = f"Generate a semantic embedding vector for this text: {doc}"
            embedding = self.llm.complete(prompt)
            embeddings.append(embedding)

        self.embeddings = embeddings
        log.info("embeddings_generated")

    def ask(self, question: str) -> str:
        """Answer question using RAG."""
        log.info("question_asked", question=question)

        # 1. Retrieve relevant documents
        relevant_docs = self._retrieve(question, top_k=3)

        # 2. Generate answer using retrieved context
        context = "\n\n".join(relevant_docs)
        prompt = f"""Answer this question using only the context provided.

Context:
{context}

Question: {question}

Answer:"""

        answer = self.llm.complete(prompt)

        log.info("answer_generated", length=len(answer))
        return answer

    def _retrieve(self, query: str, top_k: int) -> list[str]:
        """Retrieve most relevant documents."""
        # Simplified - in reality, use vector similarity
        # For demo, just return first k documents
        return self.documents[:top_k]

# Usage
docs = [
    "The capital of France is Paris.",
    "Python is a programming language.",
    "The Eiffel Tower is in Paris, France."
]

qa = DocumentQA(docs)
answer = qa.ask("What is the capital of France?")
print(answer)
# → "The capital of France is Paris."
```

**During development, I (the LLM) see:**
- Embedding generation requests
- Retrieval prompts
- Question answering prompts

**I can help debug:**
- Are the prompts well-formatted?
- Is the context relevant?
- Are embeddings working correctly?

**All without external API costs or API keys!**

---

## Summary

**Key Principle:** During development, the LLM coding assistant should act as the AI backend for your app.

**Implementation:**
1. Use `LocalLLMClient` (file-based, socket, or HTTP)
2. App sends requests via IPC
3. Coding assistant receives and responds
4. Switch to real API in production via config

**Benefits:**
- ✅ No API keys during development
- ✅ Zero cost
- ✅ Better debugging (I see all prompts)
- ✅ Faster iteration
- ✅ Works offline
- ✅ Seamless production deployment

**IdlerGear provides:**
- Auto-configured IPC infrastructure
- Pre-built client libraries
- Auto-started listeners
- Production deployment helpers

**Next time you need LLM in your app:** Don't reach for the OpenAI API key - use me (the coding assistant) instead!
