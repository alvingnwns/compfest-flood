# ResiliChain AI Backend

FastAPI backend for the offline-first historical flood replay MVP. The frontend API contract is defined in [`../docs/BACKEND_INTEGRATION_CONTRACT.md`](../docs/BACKEND_INTEGRATION_CONTRACT.md).

## Setup

Use Python 3.12 or newer.

```powershell
cd be
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Check `http://localhost:8000/health`. The endpoint is internal; frontend-facing endpoints will be added according to the integration contract.
