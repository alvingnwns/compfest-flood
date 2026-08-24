from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.business_import.mapper import map_business_data
from app.business_import.parser import parse_xlsx
from app.business_import.repository import business_snapshot_repository
from app.business_import.schemas import BusinessImportResponse, BusinessSnapshot
from app.business_import.validator import validate_workbook
from app.errors import ApiError
from app.repositories.scenario_repository import get_historical_jakarta

MAX_FILE_SIZE = 5 * 1024 * 1024
SNAPSHOT_TTL = timedelta(hours=2)
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def import_business_workbook(filename: str, content_type: str | None, contents: bytes) -> BusinessImportResponse:
    lower_name = filename.lower()
    if not lower_name.endswith(".xlsx") or lower_name.endswith(".xlsm"):
        raise ApiError(422, "UNSUPPORTED_FILE_TYPE", "Upload a macro-free .xlsx workbook.")
    if content_type and content_type not in {XLSX_MIME, "application/octet-stream"}:
        raise ApiError(422, "UNSUPPORTED_MEDIA_TYPE", "The uploaded file is not an Excel .xlsx workbook.")
    if not contents:
        raise ApiError(422, "EMPTY_FILE", "The uploaded workbook is empty.")
    if len(contents) > MAX_FILE_SIZE:
        raise ApiError(422, "FILE_TOO_LARGE", "The workbook exceeds the 5 MB upload limit.")
    parsed, parse_issues = parse_xlsx(contents)
    validated, validation_issues = (
        validate_workbook(parsed, get_historical_jakarta()) if not parse_issues else (None, [])
    )
    issues = [*parse_issues, *validation_issues]
    if issues or validated is None:
        raise ApiError(
            422,
            "BUSINESS_DATA_VALIDATION_FAILED",
            "The workbook contains validation errors.",
            details={
                "valid": False,
                "errors": [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in issues],
            },
        )
    products, orders, inventory, materials, summary = map_business_data(validated, get_historical_jakarta())
    now = datetime.now(UTC)
    snapshot = business_snapshot_repository.save(
        BusinessSnapshot(
            id=f"business-{uuid.uuid4().hex[:12]}",
            created_at=now,
            expires_at=now + SNAPSHOT_TTL,
            products=products,
            orders=orders,
            inventory=inventory,
            materials=materials,
            summary=summary,
        )
    )
    return BusinessImportResponse(
        business_snapshot_id=snapshot.id,
        expires_at=snapshot.expires_at,
        summary=snapshot.summary,
        products=snapshot.products,
        inventory=snapshot.inventory,
    )


def get_business_snapshot(snapshot_id: str) -> BusinessSnapshot:
    snapshot = business_snapshot_repository.get(snapshot_id)
    if snapshot is None:
        raise ApiError(
            404,
            "BUSINESS_SNAPSHOT_NOT_FOUND",
            "The custom business snapshot was not found or has expired. Upload the workbook again.",
            details={"businessSnapshotId": snapshot_id},
        )
    return snapshot
