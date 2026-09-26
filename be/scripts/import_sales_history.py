"""Import historical daily sales from a CSV file into the inventory database.

Usage:
    python scripts/import_sales_history.py path/to/sales.csv --dry-run   # validate only, nothing is saved
    python scripts/import_sales_history.py path/to/sales.csv             # validate and save
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.errors import ApiError  # noqa: E402
from app.inventory.db import connect  # noqa: E402
from app.inventory.operations import _json_ready  # noqa: E402
from app.inventory.sales_history import import_sales_history  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import historical daily sales for forecasting.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Validate and report, then roll back.")
    args = parser.parse_args()
    content = args.csv_path.read_bytes()
    with connect(Settings()) as connection:
        try:
            result = import_sales_history(
                connection,
                content,
                filename=args.csv_path.name,
                idempotency_key=None,
                correlation_id="CLI_SALES_HISTORY_IMPORT",
            )
        except ApiError as error:
            connection.rollback()
            print(json.dumps({"error": error.code, "message": error.message, "details": error.details}, indent=2))
            return 1
        if args.dry_run:
            connection.rollback()
            print("DRY RUN: nothing was saved.")
    print(json.dumps(_json_ready(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
