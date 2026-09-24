# MakerGuide

A proof-of-concept Retrieval-Augmented Generation (RAG) service that answers questions about craft materials (resin, casting and similar) using documents you upload, with inline citations back to the source document and page.

Everything runs locally: FastAPI, PostgreSQL with pgvector, and Ollama for both embeddings and text generation. No hosted LLM APIs are used.

## Why RAG

Material instructions such as mixing ratios, cure times, temperatures and PPE are product-specific. A general-purpose LLM will confidently make these up. This project explores keeping the model grounded in manufacturer and guide documents:

- answers are generated only from retrieved passages;
- every source passage has a numbered citation, and citations or URLs the model invents are removed;
- the sources list attached to the answer is built by the application from retrieval results, not written by the model.

## Architecture

```
            ┌──────────────────────────── FastAPI (api) ────────────────────────────┐
 upload ──► │ extract text ─► chunk ─► embed ─────────────► store chunks + vectors  │
            │                                                                       │
  /ask  ──► │ embed query ─► vector search ─► build prompt ─► generate ─► clean up  │
            └──────┬───────────────────────┬──────────────────────────┬─────────────┘
                   │                       │                          │
          Ollama /api/embed        PostgreSQL + pgvector       Ollama /api/chat
          (nomic-embed-text)                                    (gpt-oss:20b)
```

Code layout: `app/api` (routers) → `app/services` (pipeline logic) → `app/repositories` (SQLAlchemy queries) → `app/models`. Schema changes are managed with Alembic (`alembic/versions`).

| Path | Purpose |
| --- | --- |
| `app/services/extraction.py` | PDF (per page, via `pypdf`), Markdown and plain-text extraction |
| `app/services/chunking.py` | Paragraph/sentence-aware chunking with overlap |
| `app/services/embedding.py` | Ollama embedding client with a dimension check |
| `app/repositories/knowledge.py` | pgvector cosine search and metadata filters |
| `app/services/rag.py` | Prompt construction and the `/ask` flow |
| `app/services/citations.py` | Citation numbering, answer cleanup, sources block |
| `app/services/conversation.py` | Conversation history window |
| `scripts/evaluate_rag.py` | Retrieval and answer evaluation against a running API |

## How it works

### Ingestion: `POST /knowledge/documents`

1. **Upload** a `.pdf`, `.md`/`.markdown` or `.txt` file (multipart) with a `title` and optional `source_url`, `manufacturer`, `material` and `category` metadata.
2. **Text extraction.** PDFs are extracted page by page, so each chunk keeps its page number. Text files are decoded as UTF-8, with a cp1252 fallback. Markdown is treated as plain text. Scanned PDFs are not OCR'd, so they are rejected as having no text.
3. **Chunking.** Paragraphs are packed into chunks of up to `CHUNK_SIZE` characters (default 800) with about `CHUNK_OVERLAP` characters (default 150) carried over from the previous chunk. Paragraphs that are too long are split by sentence, then by a hard character split. Chunks never span a page break, and no overlap is carried across one, so a chunk's page number is correct for all of its text.
4. **Embeddings.** All chunks go to Ollama's `/api/embed` (`EMBEDDING_MODEL`, default `nomic-embed-text`, 768 dimensions) in a single request. The returned vector size is checked against `EMBEDDING_DIMENSION`.
5. **Storage.** One `knowledge_documents` row plus `knowledge_chunks` rows with a `vector(768)` column are written in a single transaction.

### Retrieval: `POST /knowledge/search`

- The query is embedded with the same model. Chunks are ranked by pgvector cosine distance (`<=>`), and `score = 1 - distance`.
- Optional `manufacturer`, `material` and `category` filters are case-insensitive substring (`ILIKE`) matches on document metadata. `material` also matches "manufacturer material" combined, so `"Jesmonite AC100"` matches manufacturer `Jesmonite` with material `AC100`.
- Search is exact (a sequential scan). There is no HNSW or IVFFlat index, which is fine at proof-of-concept scale.

### Answering: `POST /ask`

1. **Conversation.** If `conversation_id` is given, the last `CONVERSATION_WINDOW_MESSAGES` messages are loaded. Otherwise a new conversation is created.
2. **Retrieval query.** The question is expanded with up to two previous user messages (`Related task: ...`) so follow-ups like "how long does it cure?" still retrieve the right material. The top `RAG_TOP_K` chunks (default 5) are retrieved.
3. **Citations.** Chunks are grouped by (document, page), and each group gets a number `[1]`, `[2]`, and so on.
4. **Prompt.** The system prompt tells the model to answer from the supplied context, not to invent product-specific values, to prefer manufacturer documentation, to treat retrieved text and chat history as data rather than instructions, and to cite only the given numbers. Each source goes into the user prompt as a `<source citation="[n]">` block with its metadata, followed by the (clipped) recent conversation and the question.
5. **Generation.** A non-streaming call to Ollama's `/api/chat` (`OLLAMA_LLM_MODEL`, default `gpt-oss:20b`).
6. **Post-processing.** The answer is cleaned up: any sources section the model wrote is removed, citation numbers not in the source list are removed, full-width brackets such as `【1】` become `[1]`, and URLs that are not a retrieved source's `source_url` are removed. A `Sources:` block built from the retrieval metadata is then appended.
7. **Response.** It contains `answer`, a structured `sources` list and `conversation_id`. Both turns are saved to the conversation. With `"diagnostics": true`, the response also includes the retrieved chunks, the full LLM prompt, and embedding, retrieval and generation timings.

Example:

```bash
curl -X POST http://localhost:8140/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How can I reduce bubbles when pouring resin dice?", "category": "resin-casting"}'
```

## Running it

Requirements: Docker with Compose. Generation with `gpt-oss:20b` needs a machine with enough memory for a 20B model. The Compose Ollama service has no GPU configuration, so on CPU expect slow answers (the default LLM timeout is 600 s). A smaller model can be set with `OLLAMA_LLM_MODEL`.

```bash
cp .env.example .env                      # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull gpt-oss:20b
curl http://localhost:8140/health         # {"status":"ok","api":"ok","postgres":"ok"}
```

The API is published on host port `8140` (`API_PORT`). Postgres (`5432`) and Ollama (`11434`) are published on `127.0.0.1` only. Interactive API docs are at `http://localhost:8140/docs`.

`/health` checks the API and Postgres (it returns HTTP 503 if Postgres is unreachable). It does not check Ollama. An Ollama problem shows up as a 503 from ingestion, search or `/ask`.

Upload a document:

```bash
curl -X POST http://localhost:8140/knowledge/documents \
  -F "file=@resin-guide.txt" -F "title=Resin casting guide" \
  -F "material=Epoxy Resin" -F "category=resin-casting"
```

### Configuration

All settings are environment variables (see `.env.example`; defaults are in `app/core/config.py`):

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://makerguide:makerguide@postgres:5432/makerguide` | Local development credentials only |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSION` | `nomic-embed-text` / `768` | The dimension is fixed into the schema by migration 002. Changing it requires recreating the database. |
| `OLLAMA_LLM_MODEL` / `OLLAMA_LLM_TIMEOUT_SECONDS` | `gpt-oss:20b` / `600` | |
| `RAG_TOP_K` | `5` | Chunks retrieved for `/ask` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `150` | Characters. Applied at ingestion time. |
| `CONVERSATION_WINDOW_MESSAGES` / `CONVERSATION_MESSAGE_MAX_CHARS` | `6` / `400` | History included in the prompt |

## Testing and evaluation

**Unit tests** cover the parts of the pipeline that don't need external services: chunking (size limits, overlap, page boundaries), extraction (file-type detection, text normalisation and decoding) and citation handling (grouping, removing invented citations and URLs, the sources block). They don't need Postgres or Ollama.

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

There are no automated tests for the database queries, the Ollama clients or the API endpoints. Those were checked manually against the running stack.

**RAG evaluation.** `scripts/evaluate_rag.py` runs the cases in `evaluation/questions.json` against a running API. It uses only the Python standard library.

```bash
python scripts/evaluate_rag.py      # MAKERGUIDE_BASE_URL defaults to http://localhost:8140
```

For each question it reports:

- **retrieval hit@1/3/5**: whether the expected document's filename is among the top-k `/knowledge/search` results;
- **average top-1 similarity**: the mean score of the best-ranked chunk;
- **concept coverage**: the fraction of expected keywords found in the `/ask` answer text (a simple case-insensitive substring check, not a semantic judgement).

The source documents the questions refer to (`casting-guide.pdf`, `resin-guide.txt`, `ac100-marble.txt`) are **not included in the repository**. Ingest them, with metadata matching the filters in `questions.json`, before running the evaluation. The evaluation set is small (5 questions) and is meant as a regression check, not a benchmark.

## Limitations

- Supported inputs are PDF (text layer only, no OCR), Markdown (parsed as plain text) and plain text. There are no tables, images or layout-aware extraction.
- Chunk sizes are measured in characters, not tokens.
- All chunks from a document are embedded in one request with a 120 s timeout, so very large documents may time out.
- There is no document delete or update endpoint and no duplicate detection. Re-uploading a file creates a second copy.
- There is no upload size limit, authentication or rate limiting. It is intended for local use only.
- Retrieval is vector similarity only. There is no hybrid/keyword search, re-ranking or vector index.
- Grounding is enforced by the prompt and by removing invented citations and URLs afterwards. The model can still state something the cited passage doesn't support. There is no automated faithfulness check.
- `/ask` responses are not streamed.

## Licence

See [PORTFOLIO.md](PORTFOLIO.md). The source is published for portfolio review only.
