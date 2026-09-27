# HW4: Campus Customs Shop + Chatbot

A Campus Customs (Yale apparel) storefront with an AI shop assistant, for MGT 409, Homework 4.

- **Front end:** React + Vite + TypeScript (`frontend/`). Home, Products (filters, sort), product pages, About, Log in / Create account, and a chat widget on every page.
- **Back end:** FastAPI (`backend/main.py`) with a PydanticAI agent defined in four files: `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py`, `backend/models.py`.
- **What the assistant does:** answers price and stock questions from the database, puts search results on the Products page as cards, suggests in-stock alternatives, asks clarifying questions, remembers logged-in shoppers, understands "this" on product pages, and logs every run to `output/audit_trail.json`.

Full system documentation: **[output/harness.md](output/harness.md)**.

## Repository layout

```
hw4/
├── AI_prompts.md            # prompts I typed for each problem
├── requirements.txt         # Python dependencies (backend)
├── .env.example             # copy to .env and add your key
├── .gitignore
├── README.md
├── frontend/                # Vite React TypeScript app
├── backend/
│   ├── main.py              # FastAPI app (uvicorn main:app --reload --port 8000)
│   ├── agent.py             # PydanticAI agent setup + chat run
│   ├── models.py            # Pydantic models (API, tools, audit)
│   ├── tools.py             # agent tools (search, stock, alternatives…)
│   ├── prompts/prompt.md    # system prompt (voice, rules, safety)
│   ├── auth.py              # accounts / login
│   ├── database.py          # SQLite helpers
│   └── audit.py             # append-only audit trail
└── output/
    ├── harness.md           # how the whole system works
    ├── design.md            # Problem 10 design write-up
    ├── usability.md         # Problem 9 improvements
    ├── app_check.html       # Problem 11 live-site check (double-click to open)
    ├── app_check_images/    # screenshots used by app_check.html
    └── audit_trail.json     # append-only log of agent runs
```

## 1. Add the local data pack (not in git)

The database and product images are **not** in this repo. Put the course data pack inside this folder like this:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/            # product images referenced by the catalogue
```

The backend looks for `data/campus_customs.db` automatically. To use a different folder, set `CAMPUS_DATA_DIR=/path/to/folder`.

## 2. Add your API key

```bash
cp .env.example .env
# then edit .env and set PORTKEY_API_KEY=<your key>
```

`.env` stays on your machine; `.gitignore` keeps it out of git. The key is only used by the backend.

## 3. Run the back end (port 8000)

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd backend
uvicorn main:app --reload --port 8000
```

Check it's up: <http://localhost:8000/api/health> should return `{"status": "ok", ...}`.

## 4. Run the front end (port 5173)

Requires Node.js 20+. In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **<http://localhost:5173>**. Vite forwards `/api` and `/media` requests to the backend on port 8000, so start the backend first.

## 5. Try it

- **Test account:** `test@campuscustoms.yale.edu` / `password`, or create your own account.
- **Sample chat questions:**
  - "What hoodies do you have?": cards appear on the Products page.
  - "Is the Boola Boola T-Shirt in medium? How much is it?": exact stock and price from the database.
  - On the Ice Hockey Left Chest Hoodie page: "is this available in medium?": sold out, with in-stock alternatives.
  - "Show me stuff": a clarifying question with tappable chips.
- **Logged-in memory:** log in, chat, log out, log back in. Your conversation is restored.
- **Audit trail:** every chat message appends an entry to `output/audit_trail.json`.
