# 🎬 VidIntel

**Ask any YouTube video a question — get an answer grounded in the transcript, with a timestamp you can click to jump straight there.**

Runs entirely on your own machine via [Ollama](https://ollama.com). No OpenAI/Anthropic key, no per-request API cost, no data leaving your computer.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(local)-000000?logo=ollama&logoColor=white)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What it does

Paste a YouTube video or playlist link. VidIntel fetches the real transcript, builds a searchable index, and gives you:

- An **automatic summary** and **key takeaways**
- **Suggested questions** to get started
- A chat interface where every answer is **grounded in the transcript** — no hallucinated facts
- **Clickable timestamp citations** on every answer that jump the embedded player to that exact moment
- **"Ask about this moment"** — ask a question about whatever's currently playing
- **Playlist support** — ask across an entire playlist, or scope a question to one video

```
Paste URL → Analyze → Transcript indexed → Summary shown → Ask questions → Click a source → Video jumps there
```

<!-- Add a screenshot or short GIF of the app here -->
<!-- ![VidIntel screenshot](docs/screenshot.png) -->

---

## Table of contents

- [Why local?](#why-local)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
  - [1. Ollama](#1-ollama)
  - [2. Backend](#2-backend)
  - [3. Frontend](#3-frontend)
- [Configuration](#configuration)
- [Running tests](#running-tests)
- [API reference](#api-reference)
- [How retrieval stays accurate](#how-retrieval-stays-accurate)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Why local?

VidIntel runs its LLM through Ollama on your own hardware instead of calling a hosted API. That means:

- **No API costs** — indexing and querying are free after the one-time model download
- **No transcript data sent to a third party** — everything stays on your machine
- **Works offline** once the video is indexed and the model is pulled

The trade-off is that answer quality depends on the local model you choose (see [Configuration](#configuration)) and on your hardware.

---

## Tech stack

| Layer | Technology |
|---|---|
| LLM runtime | [Ollama](https://ollama.com) (local inference) |
| Embeddings | `sentence-transformers` — multilingual MiniLM |
| Reranking | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) |
| Vector store | FAISS (on-disk, cached per resource) |
| Backend | FastAPI, LangChain, Pydantic v2 |
| Transcript source | `youtube-transcript-api` |
| Video/playlist metadata | `yt-dlp` (primary), `pytube` (fallback) |
| Frontend | React 18, TypeScript, Vite |
| Testing | `pytest`, TypeScript strict mode, ESLint |

---

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI routes: /api/analyze, /api/query, /health
│   │   ├── schemas.py            # Single source of truth for request/response models
│   │   └── utils/
│   │       ├── resource.py       # YouTube URL/ID parsing
│   │       ├── transcript.py     # Transcript fetch + timestamp-accurate chunking
│   │       ├── playlist.py       # Playlist → video ID expansion
│   │       ├── youtube_meta.py   # Title/channel/duration/thumbnail
│   │       ├── embedding.py      # Cached embedding + reranker models
│   │       ├── vector_store.py   # FAISS index build/load/invalidate
│   │       ├── rag.py            # Retrieval, reranking, grounded answer generation
│   │       ├── summary.py        # Summary / key takeaways / suggested questions / moments
│   │       ├── lang.py           # English / Hindi / Hinglish detection
│   │       ├── rate_limit.py     # In-process rate limiter (no Redis needed)
│   │       └── registry.py       # Tracks which resources have been analyzed
│   ├── tests/                    # pytest suite (unit + mocked integration)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Top-level workflow orchestration
│   │   ├── api/client.ts          # Typed API client
│   │   ├── types/index.ts         # Mirrors backend/app/schemas.py
│   │   └── components/
│   │       ├── resource/          # URL input, status banners
│   │       ├── video/             # Player, playlist switcher, "ask this moment"
│   │       ├── summary/           # Summary, takeaways, suggested questions
│   │       └── chat/              # Conversation, source citations, copy button
│   ├── package.json
│   └── .env.example
├── ollama/
│   └── Modelfile                  # Tuned custom model (grounding rules + sampling params)
└── README.md
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) installed
- ~2–5 GB free disk space, depending on which model you pull

### 1. Ollama

```bash
ollama pull llama3.2:3b-instruct-q4_K_M
ollama serve
```

Or build the tuned model that ships with this repo (recommended — it bakes in grounding rules and sampling parameters suited to RAG):

```bash
cd ollama
ollama create youtube-rag-model -f Modelfile
```

> **Tight on disk?** (e.g. Google Cloud Shell's 5 GB quota) Stick to a 1B–3B model. An 8B model is ~4.9 GB and often won't fit. See the comments in [`ollama/Modelfile`](ollama/Modelfile) for size/quality trade-offs, and the [Colab notebook](#running-in-colab) below for a GPU-backed alternative.

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

The first request will download the embedding/reranker models from Hugging Face (a few hundred MB, one-time).

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open **http://localhost:5173** and paste a YouTube URL.

### Running in Colab

Ollama needs a persistent background process and isn't a natural fit for Colab's notebook execution model, but it's workable:

```python
# In a Colab cell
!curl -fsSL https://ollama.com/install.sh | sh
import subprocess, time
subprocess.Popen(["ollama", "serve"])
time.sleep(5)
!ollama pull llama3.2:3b-instruct-q4_K_M
```

Then run the FastAPI backend in another cell with `nohup`/`&` and expose it with `ngrok` or Colab's port forwarding, and point a locally-run frontend at that URL via `VITE_API_URL`. A GPU Colab runtime will noticeably speed up embedding/reranking.

---

## Configuration

All backend settings live in `backend/.env` (see `backend/.env.example` for the full list with defaults):

| Variable | Purpose |
|---|---|
| `OLLAMA_HOST` | Ollama server URL (default `http://localhost:11434`) |
| `OLLAMA_MODEL` | Model tag to use for answers/summaries |
| `EMBEDDING_MODEL` | Hugging Face embedding model |
| `RERANKER_MODEL` | Cross-encoder reranker model |
| `FAISS_INDEX_PATH` | Where vector indexes are cached on disk |
| `MAX_PLAYLIST_VIDEOS` | Cap on videos processed per playlist |
| `CHUNK_MAX_CHARS` | Target size of each transcript chunk |
| `RETRIEVE_TOP_K` / `RERANK_TOP_K` | Retrieval and reranking depth |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | In-process rate limiting |
| `FRONTEND_ORIGIN` | Allowed CORS origin in production mode |

Frontend config lives in `frontend/.env`:

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Backend base URL (default `http://localhost:8000`) |

---

## Running tests

```bash
cd backend
pytest -q
```

The suite runs fully offline for URL parsing and transcript-chunking logic. A few tests additionally verify real retrieval/timestamp accuracy and the full analyze → query pipeline end-to-end — these need network access to download the embedding model on first run and are skipped automatically without it.

Frontend:

```bash
cd frontend
npm run lint
npx tsc -b
npm run build
```

---

## API reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/analyze` | `POST` | Fetch transcript(s), build the index, generate summary/takeaways/suggested questions |
| `/api/query` | `POST` | Ask a question about an already-analyzed resource |
| `/health` | `GET` | Liveness check |

Interactive docs are available at `http://localhost:8000/docs` when `PROD_MODE=false`.

---

## How retrieval stays accurate

- **Real timestamps, not estimates.** Each chunk's `start`/`end` come directly from the transcript entries it contains — never interpolated from character position over total video duration.
- **Grounded answers only.** The model is instructed to answer strictly from retrieved context and to say so plainly when the transcript doesn't cover something, rather than guessing.
- **Structured citations.** Timestamps shown to the user come from the backend's retrieval results, not from the LLM's own text — the model never has to "remember" a timestamp correctly.
- **Reranking.** Initial similarity search results are reranked with a cross-encoder before being used as context, improving precision over raw vector similarity alone.

---

## Known limitations

- **Playlist and metadata fetching** (`yt-dlp`/`pytube`) scrape YouTube's page structure rather than using the official Data API, so they can break when YouTube changes its site.
- **Video metadata** (title/channel/duration) is best-effort; if it fails, transcript Q&A still works.
- **Summaries and "important moments"** are LLM-generated and therefore best-effort in *content*, though their timestamps are always real (mapped from actual transcript chunks).
- **Single-process design.** FAISS caching and rate limiting are in-process, appropriate for a self-hosted/personal deployment rather than a multi-tenant service.

---

## Contributing

Issues and pull requests are welcome. Before opening a PR:

1. Run `pytest -q` in `backend/` and `npm run lint && npx tsc -b` in `frontend/`.
2. Keep `backend/app/schemas.py` and `frontend/src/types/index.ts` in sync — they mirror each other field-for-field.
3. Describe what changed and why in the PR description.
