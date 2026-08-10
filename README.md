# ResiliChain AI

ResiliChain AI is a flood-aware supply-chain recovery decision-support project. This repository keeps the completed Next.js frontend, the shared frontend/backend API contract, and a reserved location for the future FastAPI backend in one simple repository.

## Repository structure

```text
/
├── fe/       # Completed Next.js frontend
├── be/       # FastAPI backend foundation
├── docs/     # Shared integration documentation
├── README.md
└── .gitignore
```

The shared API handoff is documented in [`docs/BACKEND_INTEGRATION_CONTRACT.md`](docs/BACKEND_INTEGRATION_CONTRACT.md). The backend currently uses deterministic local fixtures behind replaceable engine interfaces; it does not claim real AI, routing, or optimization.

## Frontend setup

Requirements:

- Node.js 22.22+ or 24.15+
- npm 11+

```bash
cd fe
npm install
copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000/scenario`.

Mock mode is the default:

```dotenv
NEXT_PUBLIC_DATA_SOURCE=mock
NEXT_PUBLIC_API_BASE_URL=
```

To connect the future FastAPI implementation:

```dotenv
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Restart the frontend after changing public environment variables. FastAPI must implement the shared contract and allow `http://localhost:3000` through CORS.

## Frontend quality checks

Run from `fe/`:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Backend setup

```bash
cd be
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Alternatively, run the backend from the repository root with `docker compose up --build backend`. See [`be/README.md`](be/README.md) for architecture, tests, engine replacement, and current limitations.

The backend foundation has no database, authentication, real ML model, live external data, OSMnx/NetworkX routing, or OR-Tools optimizer. Simulation state is process-local and resets on restart.
