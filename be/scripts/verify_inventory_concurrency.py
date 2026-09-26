from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.errors import ApiError  # noqa: E402
from app.inventory.db import balances_base, connect  # noqa: E402
from app.inventory.operations import create_transaction, void_transaction  # noqa: E402
from app.inventory.schemas import CreateTransactionRequest  # noqa: E402


def verify() -> None:
    settings = Settings()
    with connect(settings) as connection:
        before = balances_base(connection)["ing_naga"]

    def checkout() -> tuple[str, str]:
        request = CreateTransactionRequest(
            source="POS_SIMULATOR",
            items=[{"productId": "P001", "quantity": 30}],
        )
        try:
            with connect(settings) as connection:
                _, response = create_transaction(
                    connection,
                    request,
                    idempotency_key=f"concurrency-{uuid4()}",
                    correlation_id=f"concurrency-{uuid4()}",
                )
                return "created", response["transaction"]["id"]
        except ApiError as error:
            return "rejected", error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: checkout(), range(2)))
    created = [value for status, value in results if status == "created"]
    rejected = [value for status, value in results if status == "rejected"]
    if len(created) != 1 or rejected != ["INSUFFICIENT_INVENTORY"]:
        raise AssertionError(f"Unexpected concurrency results: {results}")
    with connect(settings) as connection:
        void_transaction(
            connection,
            UUID(created[0]),
            "Automated concurrency verification reversal",
            correlation_id=f"concurrency-reversal-{uuid4()}",
        )
    with connect(settings) as connection:
        after = balances_base(connection)["ing_naga"]
    if before != after:
        raise AssertionError(f"Stock was not restored: before={before}, after={after}")
    print("CONCURRENCY_OK one checkout committed, one rejected, no oversell, stock restored")


if __name__ == "__main__":
    verify()
