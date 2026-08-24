# ARUNA Frontend

Next.js frontend for ARUNA's flood-aware supply-chain recovery decision-support MVP. Connected FastAPI mode is the default; explicit MSW mock mode exists only for isolated UI development and tests.

## Architecture

~~~text
Pages and feature views
  -> TanStack Query hooks
  -> typed services and shared HTTP client
  -> FastAPI (default) or explicit MSW mock mode
  -> Zod response validation
~~~

Simulation identity and operational condition are preserved in route search parameters. The workflow pages are:

- /scenario
- /disruption?simulation={id}
- /recovery?simulation={id}
- /impact?simulation={id}
- /copilot?simulation={id}

The UI consumes scenario/simulation lifecycle, disruption and route candidates, recovery, Impact, Custom Business Data, map context, and grounded Copilot endpoints. Impact exports support print/PDF, CSV, and JSON.

## Development

~~~powershell
npm install
npm run dev
~~~

Open http://localhost:3000/scenario. When variables are absent, API mode targets http://localhost:8000.

| Variable | Values | Purpose |
| --- | --- | --- |
| NEXT_PUBLIC_DATA_SOURCE | api or mock | Connected backend or explicit isolated mock |
| NEXT_PUBLIC_API_BASE_URL | absolute URL | FastAPI base URL |

## Runtime semantics

- Historical risk is estimated road-corridor flood exposure from the backend Random Forest, not certain closure.
- Dynamic Hazard is a historical-derived what-if simulation, not live weather or a calibrated forecast.
- Map recovery routes are pre-optimization NetworkX candidates until a ready or partial recovery result selects one.
- Recovery decisions and KPIs come from the backend CP-SAT/computation pipeline; React does not recreate them.
- Copilot is grounded in the current simulation. Per-simulation conversation UI state is bounded and stored in browser sessionStorage; backend computations remain process-local.

## Quality commands

~~~powershell
npm run lint
npm run typecheck
npm test
npm run build
~~~

## MVP boundaries

The frontend is decision support, not an execution system. It has no live weather feed. The platform has no API authentication or tenancy; snapshot IDs are not authorization. ARUNA coordinates production, warehouse allocation, downstream distribution, and fulfillment while the current backend abstracts factory-to-warehouse transfer.
