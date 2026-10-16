# AGENTS.md

## What this repo is

**Raguaco** — a conversational RAG system (document upload → embeddings → retrieval → LLM answers with sources + voice interaction). University project, team of three.

- **Currently documentation-only: there is no code, no build/test/lint tooling, nothing to run.** Don't search for manifests, lockfiles, or CI — none exist.
- `App/` holds only a UTF-16 placeholder (`some.txt`, content: "Algo"). Don't treat it as source code.
- Branch `main`, remote `origin`.

## Planned architecture (when implementation starts)

The target layout is defined in `Docs/DIAGRAMS.md` → "Estructura de rutas": a `rag_app/` Python + FastAPI app with layered structure — `app/api/routes/`, `app/core/`, `app/domain/` (models, schemas, services), `app/infrastructure/` (pgvector repo, local storage, LLM, embeddings, loaders/chunking), plus `migrations/`, `scripts/`, `docker/`, `.env.example`. Follow this structure; it's the agreed design (RNF1: modular, replaceable components).

Key product constraints traced from requirements (`Docs/Requerimientos/RF - RNF.md`, cite by ID — RF1–RF12, RNF1–RNF8):
- Answers must cite source documents and must explicitly refuse when no relevant evidence is found (RF8, RF9).
- Secrets only via environment variables, never in source; backend keys never exposed to the client (RNF5).
- Voice (STT → RAG → TTS) is the final phase, not the MVP (RF12).
- Failure in one document/query must not crash the app (RNF6).

## Diagrams (draw.io)

- Sources live in `Docs/UML/archivos/*.drawio`; exported PNGs in `Docs/UML/imagenes/*.png`. `Docs/DIAGRAMS.md` embeds the PNGs — after editing a `.drawio`, re-export the matching PNG or docs go stale.
- Draw.io temp/backup files are already gitignored (`*.drawio.bkp`, `*.dtmp`, `*.tmp`).

## Working directory

- **Always work from `App/`, never from the repo root**: start each shell/session with `cd App`, and run commands, servers, tests and Python imports as if `App/` were the project root (e.g. `uvicorn main:app`, `from api.routes.documents import router`). Don't rely on the repo root being the cwd.
- Paths quoted in this file that start with `Docs/` (and `App/` itself) remain relative to the **repo root** — they describe repo layout, not cwd-relative targets.

## Conventions

- All prose (README, Docs, commit messages) is in **Spanish**; match it when writing user-facing content. Code identifiers/comments can be English.
- Several filenames contain spaces (`RF - RNF.md`, `diagrama entidad relacion.drawio`) — quote paths in shell; Markdown links use `%20`.
