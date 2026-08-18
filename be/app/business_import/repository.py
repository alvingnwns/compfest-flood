from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from threading import Lock

from app.business_import.schemas import BusinessSnapshot


class BusinessSnapshotRepository:
    def __init__(self, max_items: int = 20) -> None:
        self._items: OrderedDict[str, BusinessSnapshot] = OrderedDict()
        self._max_items = max_items
        self._lock = Lock()

    def save(self, snapshot: BusinessSnapshot) -> BusinessSnapshot:
        with self._lock:
            self._cleanup_locked()
            self._items[snapshot.id] = snapshot
            while len(self._items) > self._max_items:
                self._items.popitem(last=False)
        return snapshot

    def get(self, snapshot_id: str) -> BusinessSnapshot | None:
        with self._lock:
            self._cleanup_locked()
            return self._items.get(snapshot_id)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _cleanup_locked(self) -> None:
        now = datetime.now(UTC)
        for key in [key for key, value in self._items.items() if value.expires_at <= now]:
            self._items.pop(key, None)


business_snapshot_repository = BusinessSnapshotRepository()
