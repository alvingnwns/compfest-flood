from __future__ import annotations

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import StreamingResponse

from app.business_import.schemas import BusinessImportResponse
from app.business_import.service import MAX_FILE_SIZE, get_business_snapshot, import_business_workbook
from app.business_import.template import create_business_template

router = APIRouter(prefix="/api/business-data", tags=["business-data"])


@router.get("/template", response_class=StreamingResponse)
def download_business_template() -> StreamingResponse:
    return StreamingResponse(
        BytesIO(create_business_template()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ResiliChain_Business_Data_Template.xlsx"'},
    )


@router.post(
    "/import",
    response_model=BusinessImportResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def import_business_data(file: Annotated[UploadFile, File()]) -> BusinessImportResponse:
    contents = await file.read(MAX_FILE_SIZE + 1)
    filename = file.filename or ""
    content_type = file.content_type
    await file.close()
    return import_business_workbook(filename, content_type, contents)


@router.get("/{snapshot_id}", response_model=BusinessImportResponse, response_model_exclude_none=True)
def get_business_data_summary(snapshot_id: str) -> BusinessImportResponse:
    snapshot = get_business_snapshot(snapshot_id)
    return BusinessImportResponse(
        business_snapshot_id=snapshot.id,
        expires_at=snapshot.expires_at,
        summary=snapshot.summary,
        products=snapshot.products,
        inventory=snapshot.inventory,
    )
