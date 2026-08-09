# ResiliChain AI

ResiliChain AI is a flood-aware supply-chain recovery decision-support project. This repository keeps the completed Next.js frontend, the shared frontend/backend API contract, and a reserved location for the future FastAPI backend in one simple repository.

## Repository structure

```text
/
├── fe/       # Completed Next.js frontend
├── be/       # Reserved for the future FastAPI backend
├── docs/     # Shared integration documentation
├── README.md
└── .gitignore
```

The backend has not been implemented. The shared API handoff is documented in [`docs/BACKEND_INTEGRATION_CONTRACT.md`](docs/BACKEND_INTEGRATION_CONTRACT.md).

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

## Backend status

`be/` is intentionally empty except for a placeholder that keeps the directory in Git. Backend, ML, routing, optimizer, and database implementation belong to a future development phase.
