# AI RAG Concepts & Deep-Dive Analysis

This document provides an in-depth look at the Retrieval-Augmented Generation (RAG) and AI methodologies driving the Maya Event Planning Voice Agent, analyzing its current capabilities, limitations, and the path forward.

---

## 1. What is RAG and Why Use It?

**Retrieval-Augmented Generation (RAG)** is an AI framework that improves the quality of language model responses by grounding the model on external sources of knowledge. In traditional conversational AI, the model only relies on its pre-trained weights or the immediate context window. As a conversation grows long, the model "forgets" earlier details due to context limits.

For Maya (our voice agent), RAG serves as the **long-term memory bank**.

### How it Works in Maya

Instead of passing the entire, massive conversation history to the LLM for every single turn, Maya chunks the conversation into individual "turns" (a User utterance and Maya's response).

1. **Embedding**: Each turn is converted into a high-dimensional vector using an embedding model.
2. **Storage**: These vectors are stored persistently in **ChromaDB**, an open-source vector database (`rag.py`).
3. **Retrieval**: When the user says something that requires past context (e.g., "Actually, change the flowers I mentioned earlier to roses"), the system performs a **semantic search**. It converts the user's intent into a vector, queries ChromaDB for the closest numerical matches (using cosine similarity), and retrieves exactly what the user said 20 turns ago.
4. **Augmentation**: This retrieved context is then injected into the LLM's prompt, allowing Maya to answer accurately without suffering from long-term memory loss.

---

## 2. Deep Analysis of the Current Implementation

The current architecture blends **Rule-Based State Extraction** with an **LLM-Augmented RAG Pipeline**.

### The Technical Stack

- **Vector Store**: `chromadb` (Persistent collection named `maya_conversations`)
- **Embeddings**: Sentence transformers (via Chroma's default `all-MiniLM-L6-v2` or OpenAI embeddings).
- **Graceful Degradation**: The architecture (`rag.py`) is designed to fail gracefully. If ChromaDB is missing or errors out, the orchestrator falls back to short-term sliding window memory (`memory.py`), ensuring the agent never crashes.
- **Continuous Ingestion**: Every time a user speaks and Maya replies, the `SessionManager` automatically chunks the interaction and triggers an upsert into ChromaDB.

### What it does well:

1. **Low Latency for Voice**: By keeping the immediate state in JSON (RFC6902 patches) and pushing massive conversation history to ChromaDB, the primary loop runs extremely fast. Voice AI demands <500ms latency; avoiding massive LLM context windows keeps Maya snappy.
2. **Handling Topic Switching**: If a user jumps from discussing "Entrance Garlands" back to "Primary Colors," the semantic search pulls the exact color preferences they mentioned 5 minutes ago to verify what they are changing.

---

## 3. Current Problems Faced

While the current implementation works, several challenges have emerged during testing:

1. **Keepalive Timeout Stalls**:
   - _Issue_: During heavy memory compression or RAG retrieval with OpenAI, the process blocked the main asynchronous event loop for several seconds. This briefly prevented the server from responding to WebSocket `ping` frames, causing the STT worker to drop the connection (`Code 1011`).
   - _Mitigation_: We introduced a `_ws_reader()` background coroutine in the STT worker to independently service keepalive pings while the main thread waits for AI computation.

2. **Context Fragmentation**:
   - _Issue_: Sometimes, user intent spans across multiple short conversational turns (e.g., Turn 1: "I want blue", Turn 2: "Actually no, pink"). RAG might retrieve Turn 1 because "blue" semantically matches the query, missing the immediate subsequent correction.
   - _Mitigation_: A combination of sliding-window (last 5 turns) + RAG (top-K historical turns) is required, avoiding strictly relying on purely historic retrieval.

3. **VAD Settings and Auto Gain**:
   - _Issue_: The Whisper STT combined with WebRTC Voice Activity Detection (VAD) struggles with amplitude. Browsers often compress microphone volume (Auto Gain Control), dropping the volume below the VAD energy threshold (`0.04`), causing Maya to ignore soft-spoken users.
   - _Mitigation_: Lowering the VAD threshold to `0.005` helped, but dynamic thresholding is still needed.

4. **Speech Synthesis hardware mutex**:
   - _Issue_: Native browser `speechSynthesis` completely blocks microphone audio capture on macOS/WebRTC due to hardware echo-cancellation locks.
   - _Mitigation_: We built a custom `/tts` endpoint delivering MP3 bytes directly to an `HTMLAudioElement`, entirely bypassing the OS-level speech engine lock so the user can "barge-in" (interrupt Maya) successfully.

---

## 4. Next Steps & Future Enhancements

To make Maya truly production-ready, the following RAG and AI optimizations are prioritized:

1. **Async LLM Execution**:
   - **Action**: Fully migrate all OpenAI API calls (in NLU parsing and memory compression) to `openai.AsyncOpenAI`.
   - **Why**: Currently, synchronous calls block the Uvicorn thread. Async execution will ensure WebSocket connections never stall, even under heavy load.

2. **Metadata Filtering in ChromaDB**:
   - **Action**: Enhance the RAG upsert to attach metadata tagging (e.g., `slot_topic: "backdrop"`, `intent: "correction"`).
   - **Why**: Semantic search alone can hallucinate. By filtering searches using metadata tags (e.g., `where={"slot_topic": "flowers"}`), retrieval becomes 100x more accurate.

3. **Hierarchical Summarization (Memory Tree)**:
   - **Action**: Implement a rolling summarization agent. Instead of just storing raw turns, a background job summarizes every 10 turns into a single "Memory Node" and embeddings those nodes instead.
   - **Why**: Reduces ChromaDB query complexity and gives the LLM a much cleaner, narrative representation of the user's event vision.

4. **Dynamic LLM Swapping**:
   - **Action**: Introduce a multi-agent router. Use open-source, local models (like Llama 3 8B) for fast intent classification (NLU), and route heavy context queries to GPT-4o.
   - **Why**: Cuts cloud API costs and dramatically reduces latency for simple slot-filling tasks.
