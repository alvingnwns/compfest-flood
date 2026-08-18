from __future__ import annotations

from typing import Any, TypeVar

from pydantic import ValidationError

from app.business_import.schemas import (
    BomImportRow,
    ImportValidationIssue,
    InventoryImportRow,
    MaterialImportRow,
    OrderImportRow,
    ParsedBusinessWorkbook,
    ProductImportRow,
)
from app.schemas.scenario import Scenario

ROW_LIMITS = {"Products": 20, "Orders": 100, "Inventory": 100, "Materials": 50, "BOM": 200}
T = TypeVar("T")


def _clean_identifier(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _row_error(sheet: str, row: int, column: str | None, code: str, message: str) -> ImportValidationIssue:
    return ImportValidationIssue(sheet=sheet, row=row, column=column, code=code, message=message)


def _validate_rows(
    sheet: str,
    rows: list[tuple[int, dict[str, Any]]],
    model: type[T],
    mapping: dict[str, str],
    issues: list[ImportValidationIssue],
) -> list[T]:
    result: list[T] = []
    if not rows:
        issues.append(
            ImportValidationIssue(sheet=sheet, code="EMPTY_SHEET", message=f"{sheet} must contain at least one row.")
        )
        return result
    if len(rows) > ROW_LIMITS[sheet]:
        issues.append(
            ImportValidationIssue(
                sheet=sheet,
                code="ROW_LIMIT_EXCEEDED",
                message=f"{sheet} has {len(rows)} rows; the maximum is {ROW_LIMITS[sheet]}.",
            )
        )
    for row_number, raw in rows:
        data = {target: _clean_identifier(raw.get(source)) for source, target in mapping.items()}
        if "unit" in data and data["unit"] in {None, ""}:
            data["unit"] = "unit"
        data["source_row"] = row_number
        try:
            result.append(model.model_validate(data))  # type: ignore[attr-defined]
        except ValidationError as exc:
            for error in exc.errors():
                field = str(error["loc"][-1]) if error["loc"] else None
                source_column = next((source for source, target in mapping.items() if target == field), field)
                issues.append(
                    _row_error(
                        sheet,
                        row_number,
                        source_column,
                        "INVALID_VALUE",
                        f"{sheet} row {row_number}, column '{source_column}' has an invalid value: {error['msg']}.",
                    )
                )
    return result


def _duplicates(
    sheet: str,
    rows: list[Any],
    key_fields: tuple[str, ...],
    column: str,
    issues: list[ImportValidationIssue],
) -> None:
    seen: set[tuple[Any, ...]] = set()
    for item in rows:
        key = tuple(getattr(item, field) for field in key_fields)
        if key in seen:
            value = " + ".join(str(part) for part in key)
            issues.append(
                _row_error(
                    sheet,
                    item.source_row,
                    column,
                    "DUPLICATE_ID",
                    f"{sheet} row {item.source_row} duplicates '{value}'.",
                )
            )
        seen.add(key)


def validate_workbook(
    parsed: dict[str, list[tuple[int, dict[str, Any]]]], demo: Scenario
) -> tuple[ParsedBusinessWorkbook | None, list[ImportValidationIssue]]:
    issues: list[ImportValidationIssue] = []
    products = _validate_rows(
        "Products",
        parsed.get("Products", []),
        ProductImportRow,
        {
            "productId": "product_id",
            "productName": "product_name",
            "sellingPrice": "selling_price",
            "unit": "unit",
        },
        issues,
    )
    orders = _validate_rows(
        "Orders",
        parsed.get("Orders", []),
        OrderImportRow,
        {
            "orderId": "order_id",
            "storeId": "store_id",
            "productId": "product_id",
            "quantity": "quantity",
            "priority": "priority",
            "deadlineMinutes": "deadline_minutes",
        },
        issues,
    )
    inventory = _validate_rows(
        "Inventory",
        parsed.get("Inventory", []),
        InventoryImportRow,
        {
            "warehouseId": "warehouse_id",
            "productId": "product_id",
            "availableQuantity": "available_quantity",
        },
        issues,
    )
    materials = _validate_rows(
        "Materials",
        parsed.get("Materials", []),
        MaterialImportRow,
        {
            "materialId": "material_id",
            "materialName": "material_name",
            "supplierId": "supplier_id",
            "availableQuantity": "available_quantity",
        },
        issues,
    )
    bom = _validate_rows(
        "BOM",
        parsed.get("BOM", []),
        BomImportRow,
        {
            "productId": "product_id",
            "materialId": "material_id",
            "quantityRequired": "quantity_required",
        },
        issues,
    )
    _duplicates("Products", products, ("product_id",), "productId", issues)
    _duplicates("Orders", orders, ("order_id",), "orderId", issues)
    _duplicates("Inventory", inventory, ("warehouse_id", "product_id"), "warehouseId", issues)
    _duplicates("Materials", materials, ("material_id",), "materialId", issues)
    _duplicates("BOM", bom, ("product_id", "material_id"), "productId", issues)

    product_ids = {item.product_id for item in products}
    material_ids = {item.material_id for item in materials}
    store_ids = {item.id for item in demo.facilities if item.kind == "store"}
    warehouse_ids = {item.id for item in demo.facilities if item.kind == "warehouse"}
    supplier_ids = {item.id for item in demo.facilities if item.kind == "supplier"}
    for order in orders:
        if order.product_id not in product_ids:
            issues.append(
                _row_error(
                    "Orders",
                    order.source_row,
                    "productId",
                    "UNKNOWN_PRODUCT",
                    f"Orders row {order.source_row} references productId '{order.product_id}', "
                    "but it does not exist in Products.",
                )
            )
        if order.store_id not in store_ids:
            issues.append(
                _row_error(
                    "Orders",
                    order.source_row,
                    "storeId",
                    "UNKNOWN_STORE",
                    f"Orders row {order.source_row} references storeId '{order.store_id}', "
                    "which is not in the Jakarta demo network.",
                )
            )
    for item in inventory:
        if item.product_id not in product_ids:
            issues.append(
                _row_error(
                    "Inventory",
                    item.source_row,
                    "productId",
                    "UNKNOWN_PRODUCT",
                    f"Inventory row {item.source_row} references unknown productId '{item.product_id}'.",
                )
            )
        if item.warehouse_id not in warehouse_ids:
            issues.append(
                _row_error(
                    "Inventory",
                    item.source_row,
                    "warehouseId",
                    "UNKNOWN_WAREHOUSE",
                    f"Inventory row {item.source_row} references warehouseId '{item.warehouse_id}', "
                    "which is not in the Jakarta demo network.",
                )
            )
    for item in materials:
        if item.supplier_id not in supplier_ids:
            issues.append(
                _row_error(
                    "Materials",
                    item.source_row,
                    "supplierId",
                    "UNKNOWN_SUPPLIER",
                    f"Materials row {item.source_row} references supplierId '{item.supplier_id}', "
                    "which is not in the Jakarta demo network.",
                )
            )
    bom_products: set[str] = set()
    bom_materials: set[str] = set()
    for item in bom:
        if item.product_id not in product_ids:
            issues.append(
                _row_error(
                    "BOM",
                    item.source_row,
                    "productId",
                    "UNKNOWN_PRODUCT",
                    f"BOM row {item.source_row} references unknown productId '{item.product_id}'.",
                )
            )
        else:
            bom_products.add(item.product_id)
        if item.material_id not in material_ids:
            issues.append(
                _row_error(
                    "BOM",
                    item.source_row,
                    "materialId",
                    "UNKNOWN_MATERIAL",
                    f"BOM row {item.source_row} references unknown materialId '{item.material_id}'.",
                )
            )
        else:
            bom_materials.add(item.material_id)
    for product in products:
        if product.product_id not in bom_products:
            issues.append(
                _row_error(
                    "Products",
                    product.source_row,
                    "productId",
                    "MISSING_BOM",
                    f"Product '{product.product_id}' has no BOM relationship.",
                )
            )
    for material in materials:
        if material.material_id not in bom_materials:
            issues.append(
                _row_error(
                    "Materials",
                    material.source_row,
                    "materialId",
                    "UNUSED_MATERIAL",
                    f"Material '{material.material_id}' is not referenced by any BOM row.",
                )
            )

    if issues:
        return None, issues
    return (
        ParsedBusinessWorkbook(
            products=products,
            orders=orders,
            inventory=inventory,
            materials=materials,
            bom=bom,
        ),
        [],
    )
