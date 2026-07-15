# AIVOA — AI-First CRM · Healthcare Professional (HCP) Module

**Log Interaction Screen** — a split-screen CRM where a pharmaceutical sales representative
speaks naturally to an AI Assistant, and a LangGraph agent extracts structured data, calls the
right tool, writes to the database, and pushes a live update into the on-screen CRM form.

The representative **never** types directly into the Interaction Details form. Every field on
the left is a live, read-only reflection of what the AI Assistant, orchestrated by LangGraph, has
understood and saved.

---

## 1. Assignment Objective

Build the Log Interaction Screen for an AI-first CRM HCP module:

- A left panel showing structured interaction data (HCP name, hospital, sentiment, products, etc.)
- A right panel with an AI chat assistant that is the *only* way to create or edit that data
- A LangGraph agent with a minimum of five tools, backed by a Groq-hosted LLM, that performs
  intent detection, entity extraction, and database writes
- A FastAPI backend, a MySQL-compatible relational database via SQLAlchemy, and a
  React + Redux frontend

## 2. Architecture

```
┌────────────┐     ┌──────────────────┐     ┌───────────────────────────┐     ┌────────────┐
│   React    │────▶│  FastAPI /chat   │────▶│      LangGraph Agent       │────▶│   MySQL /  │
│  + Redux   │◀────│    endpoint      │◀────│  (StateGraph, checkpointed)│◀────│  SQLite    │
└────────────┘     └──────────────────┘     └───────────────────────────┘     └────────────┘
                                                   │
                                        ┌──────────┴───────────┐
                                        │  Groq LLM (openai/gpt-oss-20b, │
                                        │  swappable to gpt-oss-120b)   │
                                        └────────────────────────────┘
                                                   │
                     ┌──────────────┬──────────────┼──────────────┬──────────────┐
                     ▼              ▼              ▼              ▼              ▼
              log_interaction edit_interaction view_history schedule_followup recommend_next_action
```

Request flow (exactly as mandated):

```
User → React Chat Interface → FastAPI → LangGraph Agent → Intent Detection →
Tool Selection → LLM (reasoning/extraction) → Tool Execution → Database →
Update Redux State → Automatically Update Left Interaction Form
```

The LLM **never** writes to the database directly. Every database mutation happens inside a
LangGraph tool function, which calls a service/repository that owns the SQLAlchemy session.

### Why the LLM only ever "decides", never "writes"

`app/agent/graph.py` binds all five tools to the Groq model via native function-calling
(`llm.bind_tools(tools)`). The model's only two possible outputs are: (a) plain text, or (b) a
tool call with structured arguments. Tool execution — the part that touches SQLAlchemy — lives in
plain Python inside `app/agent/tools/*.py` and is invoked by the graph's `tools` node, never by
the model itself.

## 3. Tech Stack

| Layer          | Technology                                             |
|----------------|---------------------------------------------------------|
| Frontend       | React 18, Redux Toolkit, Vite, Google Inter font        |
| Backend        | Python 3.11+, FastAPI                                   |
| AI Orchestration | LangGraph (`StateGraph`, checkpointed memory)          |
| LLM            | Groq API — `openai/gpt-oss-20b` (default), swappable to `openai/gpt-oss-120b`. The assignment-specified `gemma2-9b-it` / `llama-3.3-70b-versatile` have since been deprecated by Groq; `app/agent/llm.py` auto-maps them to current equivalents if ever configured. |
| Database       | MySQL (via `DATABASE_URL`); SQLite by default for zero-setup local runs |
| ORM            | SQLAlchemy 2.0 (typed, declarative)                      |
| Migrations     | Alembic (versioned schema changes; see `backend/alembic/README.md`) |
| Validation     | Pydantic v2 / pydantic-settings                          |

## 4. Folder Structure

```
aivoa-crm/
├── backend/
│   ├── app/
│   │   ├── core/            # config.py, logging_config.py
│   │   ├── db/               # SQLAlchemy engine/session/base
│   │   ├── models/           # Doctor, Interaction, FollowUp, Product, ChatMessage
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── repositories/     # Pure data-access layer (no business logic)
│   │   ├── services/         # Business logic + serialization (interaction_service.py)
│   │   ├── agent/
│   │   │   ├── state.py      # LangGraph AgentState (TypedDict)
│   │   │   ├── llm.py        # Configurable Groq client factory
│   │   │   ├── prompts.py    # System + recommendation prompts
│   │   │   ├── graph.py      # StateGraph wiring: agent ⇄ tools
│   │   │   ├── runner.py     # Invokes the graph for one chat turn
│   │   │   └── tools/        # 5 LangGraph tools (see below)
│   │   ├── routes/           # chat, interactions, history, followups, recommendations
│   │   ├── dependencies.py
│   │   └── main.py           # FastAPI app, CORS, lifespan (DB init)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/client.js             # Axios wrapper — /chat is the only write path
    │   ├── redux/
    │   │   ├── store.js
    │   │   └── slices/               # interaction, chat, history, ui
    │   ├── components/
    │   │   ├── Sidebar/, Header/
    │   │   ├── InteractionPanel/     # AI-controlled, read-only left form
    │   │   ├── ChatPanel/            # right-side AI Assistant (only interactive surface)
    │   │   └── common/Toast.jsx
    │   ├── App.jsx / index.css
    ├── index.html                    # Google Inter font import
    └── package.json
```

## 5. Database Design

- **doctors** (HCPs): `id, name, hospital, specialty, created_at, updated_at`
- **interactions**: `id, session_id, doctor_id (FK), hospital, specialty, interaction_date,
  interaction_type, products_discussed, sentiment, brochures_shared, samples_requested,
  questions_raised, notes, discussion_summary, follow_up_date, created_at, updated_at`
- **follow_ups**: `id, interaction_id (FK), follow_up_date, notes, status, created_at, updated_at`
- **products**: `id, name, description` (reference table for product names)
- **chat_messages**: `id, session_id, role, content, tool_used, created_at` (conversation audit log)

Relationships: `Doctor 1—N Interaction`, `Interaction 1—N FollowUp`.

## 6. LangGraph Workflow

`app/agent/graph.py` builds a two-node `StateGraph` per request (tools are closed over the
request's DB session and `session_id`):

```
        ┌────────────────────────────┐
 START ▶│  agent (Groq LLM + tools)  │
        └──────────────┬─────────────┘
                        │ tool_calls present?
              ┌─────────┴─────────┐
              ▼ yes                ▼ no
        ┌───────────┐            END
        │   tools    │
        └─────┬──────┘
              │ back to agent for a natural-language reply
              ▼
        ┌────────────────────────────┐
        │  agent (final synthesis)  │
        └──────────────┬─────────────┘
                        ▼
                       END
```

Conversation memory is checkpointed (`MemorySaver`, keyed by `session_id` as `thread_id`), so the
agent remembers what it logged earlier in the conversation — which is how "edit interaction"
requests like *"Actually the doctor's name was Dr. John"* resolve to the correct record without
the user repeating the interaction ID.

### The Five LangGraph Tools

1. **`log_interaction`** — Creates a new interaction. Extracts HCP name, hospital, specialty,
   date, interaction type, products, sentiment, brochures/samples flags, questions, notes, and a
   short summary from free text, resolves/creates the `Doctor` record, and persists the row.
2. **`edit_interaction`** — Applies a partial update to the most recently logged interaction (or
   an explicit `interaction_id`). Only the fields the rep mentions change; everything else is
   preserved untouched.
3. **`view_interaction_history`** — Retrieves past interactions, filterable by HCP name and/or
   date range, sorted most-recent-first.
4. **`schedule_followup`** — Creates a `FollowUp` row tied to an interaction (resolved by
   `interaction_id`, HCP name, or defaulting to the latest interaction in the session), and
   mirrors the date onto the interaction's `follow_up_date` field.
5. **`recommend_next_action`** — Pulls an HCP's interaction history and asks the LLM to reason
   over sentiment trends, repeated product interest, and sample requests to produce 3–5 concrete,
   evidence-based recommendations (JSON array). Falls back to a small heuristic set only if the
   LLM call itself fails (e.g. network error), so a bad response never surfaces raw errors to the
   rep.

## 7. API Endpoints

| Method | Path                          | Purpose                                            |
|--------|-------------------------------|-----------------------------------------------------|
| POST   | `/api/v1/chat`                 | **Primary endpoint.** Runs one LangGraph agent turn |
| GET    | `/api/v1/interactions`         | List interactions (read/admin)                     |
| GET    | `/api/v1/interactions/{id}`    | Get a single interaction                            |
| POST   | `/api/v1/interactions`         | Direct create (REST completeness; not used by chat UI) |
| PUT    | `/api/v1/interactions/{id}`    | Direct partial update (REST completeness)           |
| GET    | `/api/v1/history/{doctor}`     | Interaction history for an HCP                      |
| POST   | `/api/v1/followup`             | Direct follow-up creation (REST completeness)        |
| POST   | `/api/v1/recommendation`       | Direct recommendation call (reuses the same tool)    |
| GET    | `/health`                      | Liveness check                                       |

> **Important:** the frontend's Interaction Details panel is populated *only* from `/chat`
> responses. The POST/PUT `/interactions` endpoints exist for API completeness and testing, but
> are intentionally not wired into any "fill the form" UI flow — that would violate the
> assignment's core requirement.

## 8. Frontend Design Notes

- **Left panel** (`InteractionPanel`): every field renders from Redux state only — there are no
  `<input>` elements with `onChange` handlers wired to the CRM data. Fields flash briefly (a
  warm amber highlight) for ~1.8s whenever the AI just wrote to them, so the rep can visually
  trace what the assistant changed.
- **Right panel** (`ChatPanel`): the sole interactive surface. Tool results for history and
  recommendations render as rich cards inline in the conversation (rather than a separate static
  tab), since in an AI-first product the conversation *is* the interface.
- **Redux state**: `interaction` (current form + which fields just changed), `chat` (message
  list, sending status), `history` (last fetched history/recommendations), `ui` (session id,
  toasts, loading/error).
- Typography is Google **Inter** throughout, loaded in `index.html`.

## 9. Installation & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Groq API key — create one free at https://console.groq.com/keys
- MySQL 8+ (this project's default/demonstrated database — see setup below)

### 1. Create the MySQL database

```sql
CREATE DATABASE aivoa_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aivoa'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON aivoa_crm.* TO 'aivoa'@'localhost';
FLUSH PRIVILEGES;
```

(Using the root user directly instead is fine too for local development — just point
`DATABASE_URL` at whichever credentials you used.)

### 2. Backend setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:
```
GROQ_API_KEY=<your key>
DATABASE_URL=mysql+pymysql://aivoa:your_password@localhost:3306/aivoa_crm?charset=utf8mb4
```
(`PyMySQL` and `cryptography` — needed for MySQL 8's default auth plugin — are already in
`requirements.txt`, so no extra driver install is needed.)

### 3. Create the schema with Alembic

MySQL's schema is owned entirely by Alembic in this project (see `app/db/session.py` —
`create_all()` deliberately only runs for the SQLite fallback, so there's a single source of
truth for schema on a real database):

```bash
# still inside backend/, venv active
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Open the generated file under `alembic/versions/` and skim it before running `upgrade` — it's
the first migration, so it's worth a quick sanity check. See `backend/alembic/README.md` for the
full workflow (what to run whenever a model changes afterward).

### 4. Start the backend and verify the connection

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/debug/db-health` — it runs a real `SELECT 1` against MySQL and
reports the connection status, dialect, and pool stats (password always redacted). Confirm you
see `"connection_status": "ok"` and `"dialect": "mysql"` before moving on. If it's not `"ok"`,
the error message there tells you exactly what's wrong (wrong password, database doesn't exist,
etc.) without needing to dig through logs.

### No MySQL available? (fallback for quick frontend-only demos)

Set `DATABASE_URL=sqlite:///./aivoa_crm.db` in `.env` instead, skip the Alembic step entirely
(tables are auto-created on startup), and start uvicorn directly. This project is built and
tested against MySQL per the assignment, but SQLite remains available so the UI/agent can still
be exercised with zero external setup.

Connection pooling (`pool_recycle=1800`, `pool_pre_ping=True`) is already tuned in
`app/db/session.py` specifically to avoid the classic "MySQL server has gone away" error
that shows up when a pooled connection sits idle past MySQL's timeout.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # defaults already point at localhost:8000
npm run dev
```

Open `http://localhost:5173`.

### Groq API Setup

1. Go to https://console.groq.com/keys and create a new API key.
2. Paste it into `backend/.env` as `GROQ_API_KEY`.
3. Default model is `openai/gpt-oss-20b`. See the note below for why this differs from the
   assignment's originally-specified model names.

### Note on Model Selection (read before assuming this is a deviation)

The assignment specifies `gemma2-9b-it` as the primary model and `llama-3.3-70b-versatile` as
context/fallback. Both are, as of this submission, retired from Groq's platform:

- **Aug 8, 2025** — Groq deprecated `gemma2-9b-it`, recommending `llama-3.1-8b-instant` as the
  direct replacement.
- **Jun 17, 2026** — Groq deprecated `llama-3.1-8b-instant` *and* `llama-3.3-70b-versatile`
  together, recommending `openai/gpt-oss-20b` and `openai/gpt-oss-120b` respectively.
  (See https://console.groq.com/docs/deprecations for Groq's current list.)

So the exact model names in the assignment are unavailable through no fault of the
implementation — both retirements happened after the assignment was written, and the second
happened after `gemma2-9b-it`'s own replacement was also retired. `openai/gpt-oss-20b` /
`openai/gpt-oss-120b` are Groq's own current official recommendations, not an arbitrary
substitution.

This is exactly why `GROQ_MODEL` / `GROQ_FALLBACK_MODEL` are environment variables rather than
hardcoded strings, and why `app/agent/llm.py` additionally auto-translates any older/deprecated
model ID at call time as a safety net (`_resolve_model()`): the architecture was built so that a
platform-side model retirement — which is entirely outside this project's control and will happen
again — never requires a code change, only a config value (or, worst case, one line in a mapping
dict).

## 10. Example Interactions to Try

```
"Today I met Dr. Smith at City Hospital and discussed Product X efficacy.
 The sentiment was positive and I shared brochures."

"Sorry, the doctor's name was actually Dr. John and the sentiment was negative."

"Show me the history for Dr. John"

"Schedule a follow-up with Dr. John for next Friday to discuss the new dosing study."

"What should I do next with Dr. John?"
```

## 11. Screenshots

_Add screenshots of the running application here before submission:_
- `docs/screenshot-log-interaction.png`
- `docs/screenshot-edit-interaction.png`
- `docs/screenshot-history.png`
- `docs/screenshot-recommendations.png`

## 12. Future Improvements

- Persistent LangGraph checkpointer (e.g. `PostgresSaver`) instead of in-memory, so conversation
  memory survives a backend restart.
- Multi-user auth (`Users` table is modeled as optional per the assignment) with per-rep session
  scoping instead of a browser-generated session id.
- Voice-note-to-text capture (referenced in the assignment's screenshot) feeding straight into
  `log_interaction`.
- Streaming token-by-token responses over SSE/WebSocket for a more responsive chat feel.
- Alembic migrations in place of `create_all` for production schema management.

---

Built as a production-quality reference implementation of an AI-first, LangGraph-orchestrated CRM
workflow for the AIVOA technical assessment.
