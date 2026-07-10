# AIVOA — AI-First CRM · Healthcare Professional (HCP) Module

**Log Interaction Screen** — a split-screen CRM where a pharmaceutical sales representative
speaks naturally to an AI Assistant, and a LangGraph agent extracts structured data, calls the
right tool, writes to the database, and pushes a live update into the on-screen CRM form.

The representative **never** types directly into the Interaction Details form. Every field on
the left is a live, read-only reflection of what the AI Assistant, orchestrated by LangGraph, has
understood and saved.

---

# AIVOA CRM — Setup & Run Guide
Two servers run side by side: 
The backend (FastAPI, port 8000) and the frontend (React/Vite, port 5173). 
# Start the backend first.
# Prerequisites
ToolVersionCheck withPython3.11 or 3.12python --versionNode.js18+node --versionnpmcomes with Nodenpm --versionGroq API keyfreeconsole.groq.com/keys
No database install needed to start — it defaults to a zero-setup SQLite file.

# Step 1 — Clone the repo
- bashgit clone <your-github-repo-url>
- cd <repo-folder-name>
You should see two top-level folders: backend/ and frontend/.

# Step 2 — Backend setup
- bashcd backend
- Create and activate a virtual environment:
- bash# Windows (PowerShell)
- python -m venv .venv
- .venv\Scripts\Activate.ps1

# macOS / Linux
- python3 -m venv .venv
- source .venv/bin/activate
- You'll know it worked because your terminal prompt now starts with (.venv).
- Install dependencies:
- bashpip install -r requirements.txt
- Set up your environment file:
- bash# Windows
- copy .env.example .env

# macOS / Linux
- cp .env.example .env
- Open backend/.env in an editor and paste your real key into this one line:
- GROQ_API_KEY=your_actual_key_here
- Everything else in .env already has working defaults (SQLite database, current Groq models) — leave the rest as-is for now.
- Start the backend:
- bashuvicorn app.main:app --reload --port 8000
- Confirm it's working — watch the terminal for a startup banner like:
======================================================================
  AIVOA backend starting | BUILD_MARKER=...
  Groq model  : raw='openai/gpt-oss-20b' -> resolved='openai/gpt-oss-20b'
  GROQ_API_KEY set: True (len=56)
  Database    : sqlite:///./aivoa_crm.db
======================================================================
INFO:     Application startup complete.
Then open http://localhost:8000/docs in a browser — you should see the interactive Swagger API docs. If that loads, the backend is healthy. Keep this terminal running.

# Step 3 — Frontend setup
- Open a new terminal window (leave the backend running in the first one).
- bashcd frontend
- Install dependencies:
- bashnpm install
- Set up the environment file:
- bash# Windows
- copy .env.example .env

# macOS / Linux
- cp .env.example .env
- Check that frontend/.env points at your backend (it should already, by default):
- VITE_API_BASE_URL=http://localhost:8000/api/v1
- Start the frontend:
- bashnpm run dev
- It will print a local URL, typically:
- Local:   http://localhost:5173/
- Open that in your browser.

# Step 4 — Test it end-to-end
In the chat panel (right side), type:
Today I met Dr. Smith at City Hospital and discussed Product X. The sentiment was positive and I shared brochures.
Expected result: the AI replies with a short confirmation, and the left "Interaction Details" panel automatically fills in — HCP name, hospital, product, sentiment, brochures shared — with no manual clicking into any field.
Try a correction next:
- Actually the doctor's name was Dr. John and the sentiment was negative.
- Only those two fields on the left panel should change; everything else stays the same.
Then try:
Show me history for Dr. John
This should render as a proper table (not raw text) below the chat.

# Troubleshooting
- Symptom: Frontend loads but chat gives a network error
- Likely cause / fix: Backend isn't running, or 'VITE_API_BASE_URL' port doesn't match the backend's --port
- Symptom: GROQ_API_KEY is not set error
- Likely cause / fix: You forgot to paste the key into backend/.env, or didn't restart uvicorn after adding it
- Symptom: pip install fails on a package
- Likely cause / fix: Confirm the virtual environment is activated ((.venv) should be visible in the prompt) before installing
- Symptom: Port 8000 or 5173 already in use
- Likely cause / fix: Something else is already running there — kill it, or start uvicorn with a different --port and update VITE_API_BASE_URL to match
- Symptom: CORS error in browser console
- Likely cause / fix: Check CORS_ORIGINS in backend/.env includes the exact frontend URL/port you're using
- Symptom: Left form doesn't update after a chat message
- Likely cause / fix: Open the browser console for JS errors first; also confirm the backend terminal shows POST /api/v1/chat returning 200 OK
- Symptom: http://localhost:8000/debug/groq-config
- Likely cause / fix: Open this directly in a browser any time to see exactly what config the running backend sees — model, whether the API key is present, database URL. Useful if something seems off.

# Stopping the app
- In each terminal, press Ctrl+C. Deactivate the Python virtual environment with deactivate if needed.
_________________________________________________________________________________________________________
_________________________________________________________________________________________________________
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
- MySQL 8+ (optional — SQLite is used automatically if you skip this)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GROQ_API_KEY=<your key>
# (optional) set DATABASE_URL to your MySQL DSN, e.g.:
# DATABASE_URL=mysql+pymysql://root:password@localhost:3306/aivoa_crm

uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (docs at `/docs`). Tables are created
automatically on startup.

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
3. Default model is `openai/gpt-oss-20b` (Groq's current recommended replacement for the
   assignment-specified `gemma2-9b-it`, which Groq has since deprecated). To switch to the
   fallback `openai/gpt-oss-120b`, either change `GROQ_MODEL` in `.env` or pass `model=` to
   `get_llm()` — no other code changes are required.

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
