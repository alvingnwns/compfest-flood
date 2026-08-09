# ResiliChain AI

Frontend-only MVP for flood-aware supply-chain recovery decision support. The application replays the Jakarta flood scenario from 04 March 2025 for Nusantara Foods and connects disruption risk to coordinated manufacturing, logistics, and commerce recommendations.

## Architecture

The UI never imports business fixtures. Pages use TanStack Query hooks, which call services through a shared HTTP client. Responses are validated with Zod before entering the UI. In mock mode, MSW intercepts the same HTTP requests a future backend will implement.

```text
Pages and feature views
  → TanStack Query hooks
  → scenario/analysis services
  → shared HTTP client
  → MSW mock API or future FastAPI
  → Zod response validation
```

Domain contracts are split across scenario/network, disruption/routes, recovery actions, and impact comparison modules. Simulation identity is preserved in the URL.

## Requirements

- Node.js 22.22+ or 24.15+ recommended
- npm 11+

## Development

```bash
npm install
copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000/scenario`.

## Environment variables

| Variable | Values | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_DATA_SOURCE` | `mock` or `api` | Selects the data source once, centrally |
| `NEXT_PUBLIC_API_BASE_URL` | URL or blank | Base URL for the future API |

Mock mode is the default when the variables are absent.

## Routes

- `/scenario`
- `/disruption?simulation=sim-jakarta-20250304`
- `/recovery?simulation=sim-jakarta-20250304`
- `/impact?simulation=sim-jakarta-20250304`

## Mock API contracts

- `GET /api/scenarios/historical-jakarta`
- `POST /api/simulations`
- `GET /api/simulations/{id}`
- `GET /api/simulations/{id}/disruption`
- `POST /api/simulations/{id}/recovery`
- `GET /api/simulations/{id}/recovery`
- `GET /api/simulations/{id}/impact`

Fixtures are deterministic contract examples in `src/mocks`; they are not component content.

## Map architecture

MapLibre renders an offline-capable neutral map canvas. Facilities, historical flood extent, risk segments, baseline route, and recovery route are separate GeoJSON sources/layers. Route geometry and road selection originate from the disruption API response.

## Stitch design source

Google Stitch project `12457697121782366283` is the development-time visual source. The selected MVP-ready screens are Scenario `24f9c4d54b684451bba47d017718f9e1`, Disruption `30616f9303a743d2b0dfebff384d2e57`, Recovery `f17a86282f054d46bd9550906cfa47a0`, and Impact `9cdea2498381485f90c5da94ad978fa4`. Stitch is never a runtime dependency.

## Quality commands

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Switching to FastAPI

1. Set `NEXT_PUBLIC_DATA_SOURCE=api`.
2. Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (or the deployed API URL).
3. Implement the endpoints above with responses matching the Zod contracts in `src/domain`.
4. Keep CORS configured for the frontend origin.
5. Restart the Next.js process. No page or visual component changes are required.

## Frontend-only limitations

Risk scores, routing, recovery recommendations, and impact figures are simulated. No ML model, optimizer, live BMKG feed, persistence, or operational execution system exists in this frontend. Operators remain the final decision makers.
