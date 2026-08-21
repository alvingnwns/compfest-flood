# Custom Business Data

## Purpose

Phase F lets a user replace the built-in operational snapshot with products, IDR selling prices, orders, inventory, materials, and BOM relationships from one macro-free Excel workbook.

**Custom Business Data replaces the demo operational snapshot, while this MVP phase continues to use ARUNA's Jakarta demo logistics network.** Suppliers, factory, warehouses, stores, vehicles, coordinates, and March replay geometry therefore remain demo data.

## Flow

```text
Excel workbook
  -> safe in-memory parser
  -> schema and referential validation
  -> typed BusinessSnapshot
  -> existing simulation and disruption analysis
  -> existing NetworkX routing
  -> existing OR-Tools recovery
  -> existing KPI calculations
```

Upload only validates and creates a preview. The Scenario page requires an explicit **Gunakan Data** confirmation before including `businessSnapshotId` in a simulation request. No upload is required for demo mode.

## Template

Download `ResiliChain_Business_Data_Template.xlsx` from `GET /api/business-data/template` or the Scenario page.

| Sheet | Required columns | Limit |
| --- | --- | ---: |
| Products | `productId`, `productName`, `sellingPrice` | 20 |
| Orders | `orderId`, `storeId`, `productId`, `quantity`, `priority`, `deadlineMinutes` | 100 |
| Inventory | `warehouseId`, `productId`, `availableQuantity` | 100 |
| Materials | `materialId`, `materialName`, `supplierId`, `availableQuantity` | 50 |
| BOM | `productId`, `materialId`, `quantityRequired` | 200 |

`Products.unit` is optional and defaults to `unit`. The concise Instructions sheet lists valid Jakarta demo IDs and current enums. Example rows are valid data and should be replaced. Selling prices are numeric IDR amounts per unit; values such as `Rp50.000` are rejected.

The current priority enum is `normal`, `high`, or `critical`. Deadlines are relative minutes, matching the existing optimizer. Each store is mapped to the preferred warehouse already used for that store in the demo scenario. Materials retain the current supplier-specific semantics through required `supplierId` values.

## Validation and security

Only `.xlsx` files are accepted, up to 5 MB. `.xls`, `.xlsm`, macros, formulas, unknown sheets/columns, missing sheets/columns, empty sheets, invalid numeric ranges, duplicate keys, oversized tables, and broken product/material/facility references are rejected with HTTP 422. Errors include `sheet`, `row`, `column`, `code`, and a user-readable `message`. Data is never silently truncated.

The parser reads workbook values in memory with external links disabled. It does not execute formulas or macros, does not use file paths supplied by the user, does not retain raw uploads, and does not log raw workbook contents.

## Demo vs custom mode

- **Demo:** the unchanged built-in Nusantara Foods operational snapshot is used; no snapshot ID is required.
- **Custom:** uploaded products, prices, orders, inventory, materials, and BOM replace those demo collections. The same demo facilities, vehicles, and Jakarta network remain in use.
- Invalid custom uploads never mutate or replace demo data.
- `businessDataSource` is `demo` or `custom`; custom simulations also expose `businessSnapshotId`.

## API

- `GET /api/business-data/template` downloads the workbook.
- `POST /api/business-data/import` validates one multipart `.xlsx` upload and returns a snapshot ID plus preview counts and total order value.
- `GET /api/business-data/{businessSnapshotId}` returns the process-local snapshot summary.
- `POST /api/simulations` accepts optional `businessSnapshotId` and otherwise defaults to demo business data.

Snapshots are bounded to 20 entries and expire after two hours. They are process-local and disappear on backend restart. A missing or expired ID returns 404 and the UI asks for another upload. This is not durable persistence.

## Computation semantics

Uploaded demand, inventory, material quantities, BOM consumption, priorities, prices, and deadlines enter the same connected solver used by demo mode. No parallel simplified optimizer exists. Uploaded orders are not mixed with fabricated demo orders.

Sales Exposure keeps the existing formula:

```text
Sales Exposure = sum(unfulfilled quantity * uploaded selling price)
```

For example, 100 requested units at IDR 50,000 with 60 recovered units leaves 40 unfulfilled units and IDR 2,000,000 of exposure.

## Privacy and Copilot

Raw workbook bytes are sent to Gemini/Qwen: **NO**.

Copilot receives only the existing bounded, parsed simulation evidence plus `businessDataSource`. When it is `custom`, Copilot may state that evidence is based on the uploaded business snapshot. It does not receive the original workbook, raw sheet rows, or arbitrary file contents.

## Real, user-provided, and demo boundaries

| Component | Status in custom mode |
| --- | --- |
| Products, prices, orders, inventory, materials, BOM | User-provided |
| Historical ML inference, NetworkX routing, OR-Tools recovery, KPIs | Real computation |
| Jakarta facilities, suppliers, factory, stores, warehouses, coordinates, vehicles | Demo |
| March replay geometry | Demo/historical snapshot context |

Safe product wording: **User-provided operational data running on the ARUNA Jakarta demo logistics network.**
