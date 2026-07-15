<div align="center">

# AIVOA — AI-First CRM
### Healthcare Professional (HCP) Module · Log Interaction Screen

**A CRM where the form fills itself.** The representative talks; a LangGraph agent listens,
decides, acts, and the screen updates in front of them.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLM%20Inference-F55036?style=flat-square)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=white)
![Redux](https://img.shields.io/badge/Redux-Toolkit-764ABC?style=flat-square&logo=redux&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8+-4479A1?style=flat-square&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-333333?style=flat-square)

</div>

> Submitted for **Aivoa.AI**'s Round 1 Technical Assessment — *AI-First CRM HCP Module: Log
> Interaction Screen*.

---

## Table of Contents

1. [What This Is](#1-what-this-is)
2. [Why It's Worth a Close Look](#2-why-its-worth-a-close-look)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Database Design](#6-database-design)
7. [The LangGraph Agent & Its 5 Tools](#7-the-langgraph-agent--its-5-tools)
8. [API Reference](#8-api-reference)
9. [Setup — Any Device, Start to Finish](#9-setup--any-device-start-to-finish)
10. [Verifying Everything Works](#10-verifying-everything-works)
11. [A 60-Second Guided Demo](#11-a-60-second-guided-demo)
12. [Engineering Decisions Worth Noting](#12-engineering-decisions-worth-noting)
13. [Troubleshooting](#13-troubleshooting)
14. [Known Limitations & Roadmap](#14-known-limitations--roadmap)

---

## 1. What This Is

A split-screen "Log HCP Interaction" workspace for pharmaceutical sales reps:

- **Left panel** — a structured CRM form (HCP name, hospital, sentiment, products discussed,
  brochures/samples, follow-up date, etc.)
- **Right panel** — an AI Assistant chat. This is the *only* way data enters the left panel.

There is no path from keyboard to database that skips the AI. The rep never clicks into a form
field. They describe what happened in plain language, and a LangGraph agent — backed by a
Groq-hosted LLM — interprets it, calls the correct tool, writes to MySQL, and the left panel
updates itself in real time.

## 2. Why It's Worth a Close Look

A few things in this build go beyond the minimum spec, specifically because they're the parts
that are easy to fake and hard to get right:

- **The LLM never touches the database — provably, not just by convention.** Tools are bound to
  Groq via native function-calling (`llm.bind_tools(...)` in `app/agent/graph.py`). The model's
  only two possible outputs are plain text or a structured tool call; every SQL statement lives in
  plain Python that the *graph* invokes, never the model. See [§12](#12-engineering-decisions-worth-noting).
- **"Which doctor?" is resolved deliberately, not guessed.** Early in this project, an ambiguous
  edit request ("set a follow-up with Dr. Khan") silently landed on the wrong doctor's record
  because the agent defaulted to "whatever was logged most recently." That failure mode has been
  designed out: `InteractionService.resolve_target_interaction()` now returns an explicit
  `ambiguous` or `not_found` result instead of guessing, and the agent asks a clarifying question
  instead of corrupting the wrong record.
- **Deletion is deliberately not an AI tool.** You can delete one or many interaction records from
  the Browse view, but that action is wired as a direct REST call, never as something a chat
  message can trigger — a natural-language "system" should not be able to destroy data on a
  misread sentence.
- **MySQL portability was actually tested, not assumed.** A few SQLAlchemy conveniences
  (`.nullslast()` for sort ordering, in particular) compile to syntax MySQL doesn't support, unlike
  Postgres/SQLite. Every ordering query in `interaction_repository.py` uses a portable `CASE`-based
  equivalent instead, specifically so this doesn't quietly work in development on SQLite and then
  break in front of an evaluator running MySQL.
- **Schema is owned by Alembic, not by app-boot side effects.** On MySQL, `create_all()` is
  deliberately never called — a real migration history is the single source of truth for schema,
  so what's in `alembic/versions/` is exactly what's running, with no drift possible.

## 3. Architecture

```
┌────────────┐     ┌──────────────────┐     ┌───────────────────────────┐     ┌────────────┐
│   React    │────▶│  FastAPI /chat   │────▶│      LangGraph Agent       │────▶│   MySQL    │
│  + Redux   │◀────│    endpoint      │◀────│  (StateGraph, checkpointed)│◀────│ (SQLAlchemy)│
└────────────┘     └──────────────────┘     └───────────────────────────┘     └────────────┘
                                                    │
                                        ┌───────────┴────────────┐
                                        │   Groq LLM              │
                                        │   openai/gpt-oss-20b     │
                                        │   (⇄ gpt-oss-120b)       │
                                        └───────────┬─────────────┘
                                                    │ bind_tools()
                     ┌──────────────┬───────────────┼───────────────┬──────────────┐
                     ▼              ▼               ▼               ▼              ▼
              log_interaction edit_interaction view_history schedule_followup recommend_next_action
```

**Mandated request flow, exactly as implemented:**

```
User → React Chat Interface → FastAPI → LangGraph Agent → Intent Detection →
Tool Selection → LLM (reasoning/extraction) → Tool Execution → Database →
Update Redux State → Automatically Update Left Interaction Form
```

The LLM **decides**; the graph's `tools` node **executes**. Nothing about database access is
hardcoded around the model — the model genuinely chooses which of the five tools to call and with
what arguments, every turn.

## 4. Tech Stack

| Layer            | Technology                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| Frontend          | React 18, Redux Toolkit, Vite, Google **Inter** font                        |
| Backend           | Python 3.11+, FastAPI                                                       |
| AI Orchestration  | LangGraph (`StateGraph`, checkpointed conversation memory)                  |
| LLM               | Groq API — `openai/gpt-oss-20b` (default), swappable to `openai/gpt-oss-120b` |
| Database          | MySQL 8+ via SQLAlchemy (SQLite available as a zero-setup fallback)         |
| ORM               | SQLAlchemy 2.0 (typed, declarative)                                         |
| Migrations        | Alembic — schema is exclusively migration-managed on MySQL                  |
| Validation        | Pydantic v2 / pydantic-settings                                             |

> **A note on the LLM models.** The assignment specifies `gemma2-9b-it` (primary) and
> `llama-3.3-70b-versatile` (fallback). Both have since been retired by Groq — `gemma2-9b-it` in
> August 2025, and `llama-3.3-70b-versatile` in June 2026 — through no fault of this
> implementation; both deprecations happened after the assignment was written. `GROQ_MODEL` /
> `GROQ_FALLBACK_MODEL` are environment variables specifically so a platform-side model retirement
> like this is a one-line config change, not a code change — `app/agent/llm.py` additionally
> auto-translates any older model ID at call time as a safety net. Full citations in
> [`backend/.env.example`](backend/.env.example).

## 5. Project Structure

```
aivoa-crm/
├── backend/
│   ├── app/
│   │   ├── core/                 # config.py (env-driven settings), logging_config.py
│   │   ├── db/                   # SQLAlchemy engine/session/base
│   │   ├── models/                # Doctor, Interaction, FollowUp, Product, ChatMessage
│   │   ├── schemas/                # Pydantic request/response contracts
│   │   ├── repositories/           # Pure data access — no business logic
│   │   ├── services/                # interaction_service.py — business rules + resolution logic
│   │   ├── agent/
│   │   │   ├── state.py            # LangGraph AgentState (TypedDict)
│   │   │   ├── llm.py              # Configurable Groq client factory + deprecation safety net
│   │   │   ├── prompts.py          # System + recommendation prompts
│   │   │   ├── graph.py            # StateGraph wiring: agent ⇄ tools
│   │   │   ├── runner.py           # Invokes the graph for a single chat turn
│   │   │   └── tools/              # The 5 LangGraph tools (§7)
│   │   ├── routes/                 # chat, interactions, history, followups, recommendations
│   │   ├── main.py                 # FastAPI app, CORS, lifespan, /debug endpoints
│   │   └── dependencies.py
│   ├── alembic/                    # Versioned schema migrations (see alembic/README.md)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/client.js            # Axios wrapper — /chat is the only write path
    │   ├── redux/slices/             # interaction, chat, history, ui
    │   ├── components/
    │   │   ├── Sidebar/, Header/
    │   │   ├── InteractionPanel/      # AI-controlled, read-only left form
    │   │   ├── ChatPanel/              # the sole interactive surface
    │   │   ├── BrowsePanel/             # record browser: search, paginate, bulk delete
    │   │   └── common/
    │   └── App.jsx / index.css
    ├── index.html                     # Google Inter font import
    └── package.json
```

## 6. Database Design

| Table            | Key Columns                                                                                          |
|-------------------|--------------------------------------------------------------------------------------------------------|
| **doctors**        | `id, name, hospital, specialty, created_at, updated_at`                                                |
| **interactions**   | `id, session_id, doctor_id (FK), hospital, specialty, interaction_date, interaction_type, products_discussed, sentiment, brochures_shared, samples_requested, questions_raised, notes, discussion_summary, follow_up_date` |
| **follow_ups**     | `id, interaction_id (FK), follow_up_date, notes, status`                                                |
| **products**       | `id, name, description`                                                                                |
| **chat_messages**  | `id, session_id, role, content, tool_used, created_at` — full conversation audit trail                 |

Relationships: `Doctor 1—N Interaction`, `Interaction 1—N FollowUp` (cascade delete — removing an
interaction removes its follow-ups).

## 7. The LangGraph Agent & Its 5 Tools

`app/agent/graph.py` builds a two-node `StateGraph` per request:

```
 START ▶ agent (Groq LLM + bind_tools) ──tool_calls?──▶ tools ──▶ agent (final reply) ▶ END
                    │no tool calls                                   ▲
                    └───────────────────────────────────────────────▶ END
```

Conversation memory is checkpointed (`MemorySaver`, keyed by `session_id`), so multi-turn
corrections like *"actually the doctor's name was Dr. John"* resolve against what was just logged,
without the rep repeating an ID.

| # | Tool | What it does |
|---|------|----------------|
| 1 | **`log_interaction`** | Extracts HCP name, hospital, specialty, date, interaction type, products, sentiment, brochure/sample flags, questions, notes, and a short summary from free text; resolves or creates the `Doctor` row; persists the interaction. |
| 2 | **`edit_interaction`** | Applies a *partial* update to an existing interaction — resolved via `interaction_id`, an HCP name, or the latest interaction in the session, through the shared, disambiguation-aware `resolve_target_interaction()`. Only mentioned fields change. |
| 3 | **`view_interaction_history`** | Retrieves past interactions filterable by one or more HCP names, hospital, product, sentiment, interaction type, and/or date range. Large result sets return a computed summary (sentiment breakdown, distinct HCPs/products, date range) instead of dumping every row into the model's context. |
| 4 | **`schedule_followup`** | Creates a `FollowUp` row against a resolved interaction and mirrors the date onto the interaction record so the left panel reflects it immediately. |
| 5 | **`recommend_next_action`** | Pulls an HCP's interaction history and asks the LLM to reason over sentiment trends, repeated product interest, and sample requests to produce 3–5 concrete, evidence-based recommendations. |

## 8. API Reference

| Method | Path | Purpose |
|--------|------|----------|
| `POST` | `/api/v1/chat` | **The** endpoint. Runs one LangGraph agent turn. |
| `GET`  | `/api/v1/interactions` | Browse/search interactions (filters, pagination) — powers the Browse panel. |
| `GET`  | `/api/v1/interactions/{id}` | Fetch a single interaction. |
| `POST` | `/api/v1/interactions` | Direct create (REST completeness; not used by the chat-driven UI). |
| `PUT`  | `/api/v1/interactions/{id}` | Direct partial update (REST completeness). |
| `DELETE` | `/api/v1/interactions/{id}` | Delete a single interaction (Browse panel only — never AI-triggerable). |
| `POST` | `/api/v1/interactions/bulk-delete` | Delete multiple interactions at once. |
| `GET`  | `/api/v1/history/{doctor}` | Interaction history for a specific HCP. |
| `POST` | `/api/v1/followup` | Direct follow-up creation. |
| `POST` | `/api/v1/recommendation` | Direct recommendation call (reuses the exact tool logic). |
| `GET`  | `/health` | Liveness check. |
| `GET`  | `/debug/db-health` | Runs a live `SELECT 1`; reports connection status, dialect, pool stats (password redacted). |
| `GET`  | `/debug/groq-config` | Reports the resolved Groq model/fallback currently active. |

Full interactive docs at **`/docs`** once the backend is running.

## 9. Setup — Any Device, Start to Finish

### Prerequisites
- Python 3.11+
- Node.js 18+
- MySQL 8+ (this project's database of record)
- A free Groq API key → https://console.groq.com/keys

### Step 1 — Create the database

```sql
CREATE DATABASE aivoa_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
(Using `root` directly is fine for local/dev use — no need to create a separate MySQL user unless
you want one.)

### Step 2 — Backend

<table>
<tr><th>macOS / Linux</th><th>Windows (PowerShell)</th></tr>
<tr valign="top">
<td>

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

</td>
<td>

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

</td>
</tr>
</table>

Edit `backend/.env`:
```
GROQ_API_KEY=<your key>
DATABASE_URL=mysql+pymysql://root:<your_password>@127.0.0.1:3306/aivoa_crm?charset=utf8mb4
```

> **If your password contains special characters** (`@`, `#`, `%`, `/`, etc.), they must be
> percent-encoded in the URL — e.g. `@` becomes `%40`. Get the exact encoded value with:
> ```bash
> python -c "from urllib.parse import quote_plus; print(quote_plus('your_password'))"
> ```

### Step 3 — Create the schema

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
Open the generated file under `alembic/versions/` and skim it before running `upgrade` — first
migration, worth a quick sanity check. See `backend/alembic/README.md` for the ongoing workflow.

### Step 4 — Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 5 — Frontend

```bash
cd frontend
npm install
cp .env.example .env      # Windows: copy .env.example .env
npm run dev
```

Open **http://localhost:5173**.

## 10. Verifying Everything Works

Before assuming anything is broken, check these two URLs — between them they answer almost every
"is it my setup or the code" question:

- **`http://localhost:8000/debug/db-health`** → expect `"connection_status": "ok"`, `"dialect": "mysql"`.
- **`http://localhost:8000/debug/groq-config`** → confirms which Groq model is actually active.

## 11. A 60-Second Guided Demo

Paste these into the AI Assistant chat, in order, to exercise all five tools plus the
Browse/delete flow:

```
1. "Today I met Dr. Smith at City Hospital and discussed Product X efficacy.
    The sentiment was positive and I shared brochures."
    → log_interaction: left panel populates automatically.

2. "Sorry, the sentiment was actually negative, not positive."
    → edit_interaction: only that field changes.

3. "Show me the history for Dr. Smith"
    → view_interaction_history: recent interactions render as a chat card.

4. "Schedule a follow-up with Dr. Smith for next Friday to discuss the new dosing study."
    → schedule_followup: follow-up date appears in the left panel.

5. "What should I do next with Dr. Smith?"
    → recommend_next_action: LLM-reasoned suggestions based on the history above.
```

Then open the **Browse** view in the sidebar, select one or more records, and delete them — note
that this is a direct UI action, not something achievable through the chat.

## 12. Engineering Decisions Worth Noting

- **`resolve_target_interaction()`** (`interaction_service.py`) is the single choke point every
  mutating tool (`edit_interaction`, `schedule_followup`) goes through to figure out *which*
  interaction a natural-language message refers to. It tries, in order: an explicit
  `interaction_id`, then a tiered doctor-name match (exact → prefix → substring), and only falls
  back to "latest in this session" if neither is given. Zero or multiple name matches return an
  explicit `not_found`/`ambiguous` status for the agent to ask about — never a silent guess.
- **Deletion is REST-only.** `bulk-delete` and `DELETE /interactions/{id}` are not registered as
  LangGraph tools, so no phrasing of a chat message can trigger a delete.
- **MySQL-safe ordering.** `_date_desc_nulls_last()` in `interaction_repository.py` replaces
  SQLAlchemy's `.nullslast()` (which MySQL's parser rejects outright) with a portable
  `CASE WHEN date IS NULL THEN 1 ELSE 0 END` expression, so sort behavior is identical across
  MySQL, Postgres, and SQLite.
- **Schema ownership.** `init_db()` in `app/db/session.py` only calls `create_all()` for the
  SQLite fallback path. On MySQL, it deliberately does nothing — Alembic is the only thing
  permitted to create or alter tables there, so there is exactly one source of truth for schema.

## 13. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `model_decommissioned` error from Groq | Assignment-specified model retired by Groq | Set `GROQ_MODEL=openai/gpt-oss-20b` in `.env` (already the default) |
| Alembic: `invalid interpolation syntax in '...%...'` | `configparser` treats `%` specially; a percent-encoded password (`%40`) trips it | Already handled in `alembic/env.py` (escapes `%` → `%%` before passing to Alembic config) |
| Alembic: `Can't locate timezone: UTC` | Windows lacks a built-in IANA timezone DB; Alembic's `timezone =` setting needs it | Already removed from `alembic.ini` — cosmetic setting only, no functional effect |
| Alembic: `Can't locate revision identified by '...'` | MySQL's `alembic_version` table remembers a migration that no longer exists on disk (e.g. after swapping project folders) | Drop & recreate the database, delete stray files in `alembic/versions/`, regenerate |
| `1064 ... near 'NULLS LAST'` | MySQL doesn't support `NULLS LAST` syntax; a SQLAlchemy `.nullslast()` call slipped back in | Already fixed in `interaction_repository.py` via `_date_desc_nulls_last()` — see §12 |
| Chat shows "couldn't reach the CRM backend" | CORS/port mismatch, or backend not actually running | Check `/health` loads directly in a browser; confirm frontend's Vite port matches `CORS_ORIGINS` in `.env` |

## 14. Known Limitations & Roadmap

- Conversation memory uses `MemorySaver` (in-process); a restart clears it. A persistent
  checkpointer (e.g. `PostgresSaver`) would carry it across restarts.
- Single implicit "rep" per browser session rather than real multi-user auth — `Users` is modeled
  as optional per the assignment.
- No mechanism yet to *explicitly clear* a field via chat (e.g. "remove the follow-up date") —
  today's `edit_interaction` only sets new values, it can't null one out. Next on the list.
- Voice-note capture (shown in the assignment's reference screenshot) is not yet implemented.

---

<div align="center">

Built as a production-quality reference implementation of an AI-first, LangGraph-orchestrated CRM
workflow.

</div>
