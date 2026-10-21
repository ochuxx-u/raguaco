# AGENTS.md

## What this repo is

**Raguaco** — a conversational RAG system (document upload → embeddings → retrieval → LLM answers with sources). Queries can be typed in the chat (RF5) or spoken via voice (RF12); both are first-class paths, and the `frontend/` app is the product's real interface. University project, team of three.

Two independent apps, no root manifest or workspace tooling:

- `App/` — Python + FastAPI backend. Entrypoint: `App/main.py` (`app = FastAPI()`). Dependencies in root `requirements.txt`.
- `frontend/` — React 19 + Vite 8 in **JavaScript** (not TS), own `package.json`. **This is the product's interface** (Landing, Dashboard, Documentos, Chat, Historial, Voz, Evidencia), not a throwaway mockup. No API calls yet (no `fetch` anywhere) — pages render static/mock UI.

## Commands

- Backend: `cd App && uvicorn main:app` (interactive docs at `/docs`). Requires PostgreSQL running and `DATABASE_URL` configured in `.env` (local setup: `Docs/Tests/TESTING_PGVECTOR.md`).
- Frontend: `cd frontend && npm install && npm run dev` (also `build`, `preview`). Requires Node `^20.19.0` or `>=22.12.0` (Vite 8).
- **No lint, typecheck, test, or CI tooling exists** — don't invent workflows or "fix" their absence. `pip-audit` in `requirements.txt` is for dependency auditing.
- AI models are not in git (`App/ai-models/` is gitignored); download per README via `hf download`: Kokoro-82M TTS and `multilingual-e5-small` embeddings. TTS needs system `espeak-ng` + `ffmpeg` (Spanish phonetics).

## Backend layout & quirks

- **Work as if `App/` were the Python project root**: start shells with `cd App`; imports are `from api.routes...` / `from domain.models...` (no `__init__.py` in `api/`; uvicorn resolves them from cwd).
- Target structure is `Docs/DIAGRAMS.md` → "Estructura de rutas" (`core/`, `domain/services/`, `infrastructure/` …). `core/`, `infrastructure/db/repositories/`, `api/routes/`, `domain/models/` and `migrations/` already exist. Follow the planned layout when adding layers (RNF1: modular, replaceable components).
- **Path quirk**: most routers mount under `/v1/models/<resource>` (`/v1/models/documents`, `/v1/models/conversations`, `/v1/models/users`); only `queries` (`/v1/queries`) and `voice` (`/v1/voice`) differ. Don't "fix" or guess these prefixes.
- Persistence goes through repositories in `infrastructure/db/repositories/` over PostgreSQL, injected with `Depends` from `api/deps.py`. `api/deps.py` provides `get_db` (one `psycopg` async connection per request from the pool in `infrastructure/db/session.py`) and the repository providers. `DATABASE_URL` comes from `.env` or the environment; the pool opens in the FastAPI lifespan and startup fails if the DB is unreachable.
- Domain models (`domain/models/`) are Pydantic with Spanish class names (`Documento`, `Usuario`, …) and are returned directly from endpoints — **there is no DTO/schemas layer** by design (see `Docs/DIAGRAMS.md`). `ModeloBase` sets `from_attributes`/`validate_assignment`/`populate_by_name`. `Documento.metadatos` accepts `metadata` as alias (matches the DB column).
- DB schema: `App/migrations/001_schema.sql` is **pasted manually into the Supabase SQL Editor** — there is no migration runner. `chunk.embedding vector(384)` must match the embedding model's dimension.

## Embeddings

- `multilingual-e5-small` requires `query: ` / `passage: ` text prefixes — without them retrieval degrades silently even though inference works. Dimension 384.
- Inference runs on `onnxruntime` + `tokenizers` (no PyTorch / sentence-transformers).
- Config lives in `.env` (copy `.env.example`; never commit — `.env*` is gitignored except the example). Model paths are **relative to `App/`** because the app runs with `App/` as root: `EMBEDDING_MODEL=ai-models/multilingual-e5-small`.

## Frontend

- **No react-router**: `src/App.jsx` switches screens via `useState(activeView)`; new screens must be added there and in `layout/Sidebar.jsx`.
- `Docs/Frontend/FRONTEND_SPEC.md` is the source of truth for all UI work. Precedence: spec → `Docs/Frontend/reference/Modificaciones_frontend.md` → mockup `RAGUACO_AI.html`. Don't invent new design. (The "Estado actual" section of `frontend/README.md` is stale.)
- Design tokens live in `src/styles/tokens.css`.

## Diagrams (draw.io)

- Sources in `Docs/UML/archivos/*.drawio`; exported PNGs in `Docs/UML/imagenes/*.png`. `Docs/DIAGRAMS.md` embeds the PNGs — after editing a `.drawio`, re-export the matching PNG or docs go stale.

## Repo quirks

- **`App/tests/` is gitignored — local tests are deliberately untracked.** Don't try to fix this.
- Filenames with spaces (`RF - RNF.md`, `diagrama entidad relacion.drawio`) — quote paths in shell; Markdown links use `%20`.
- Git flow: short commit prefixes (`Feat:`, `Fix:`, `Upd:`), Spanish; feature branches `feature/<name>` merged into `main` via PR.

## Product constraints (`Docs/Requerimientos/RF - RNF.md`, cite by ID)

- Answers must cite source documents and explicitly refuse when no relevant evidence is found (RF8, RF9).
- Secrets only via environment variables, never in source; backend keys never exposed to the client (RNF5).
- Queries can be typed (RF5) or spoken (RF12). Never describe the product as voice-only, screenless, or "no need to write": it has a full web interface and text chat is a first-class path (RF11).
- Voice (STT → RAG → TTS) is the final phase, not the MVP (RF12).
- Failure in one document/query must not crash the app (RNF6).
- Product identity (what Raguaco is, mission, vision, origin of the name) lives in `Docs/MISION_Y_VISION.md` — keep docs and user-facing copy consistent with it.

## Conventions

- All prose (README, Docs, commit messages) is in **Spanish**; match it for user-facing content. Code identifiers/comments can be English.
