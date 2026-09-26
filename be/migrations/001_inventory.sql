-- ARUNA Product Track schema. Apply with: python scripts/migrate_inventory.py
-- Quantities use normalized integers: mg for weight, µl for volume, and units for pcs.
CREATE SCHEMA IF NOT EXISTS aruna_inventory;
SET search_path TO aruna_inventory, public;

CREATE TABLE IF NOT EXISTS inventory_state (
  id smallint PRIMARY KEY CHECK (id = 1),
  inventory_version bigint NOT NULL DEFAULT 0,
  forecast_version bigint NOT NULL DEFAULT 0,
  supplier_version bigint NOT NULL DEFAULT 1,
  updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO inventory_state(id) VALUES (1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS inventory_product (
  id text PRIMARY KEY,
  name text NOT NULL,
  price_idr bigint NOT NULL CHECK (price_idr >= 0),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS inventory_ingredient (
  id text PRIMARY KEY,
  name text NOT NULL,
  category text,
  api_unit text NOT NULL CHECK (api_unit IN ('g', 'kg', 'ml', 'l', 'pcs')),
  quantity_kind text NOT NULL CHECK (quantity_kind IN ('weight', 'volume', 'discrete')),
  storage_scale bigint NOT NULL CHECK (storage_scale > 0),
  safety_stock_base bigint NOT NULL DEFAULT 0 CHECK (safety_stock_base >= 0),
  reorder_point_base bigint NOT NULL DEFAULT 0 CHECK (reorder_point_base >= 0),
  storage_capacity_base bigint CHECK (storage_capacity_base IS NULL OR storage_capacity_base >= 0),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS inventory_recipe (
  product_id text NOT NULL REFERENCES inventory_product(id),
  ingredient_id text NOT NULL REFERENCES inventory_ingredient(id),
  quantity_required_base bigint NOT NULL CHECK (quantity_required_base > 0),
  PRIMARY KEY (product_id, ingredient_id)
);
CREATE TABLE IF NOT EXISTS inventory_supplier (
  id text PRIMARY KEY,
  name text NOT NULL,
  lead_time_hours integer NOT NULL CHECK (lead_time_hours >= 0),
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS inventory_supplier_offer (
  id text PRIMARY KEY,
  supplier_id text NOT NULL REFERENCES inventory_supplier(id),
  ingredient_id text NOT NULL REFERENCES inventory_ingredient(id),
  pack_quantity_base bigint NOT NULL CHECK (pack_quantity_base > 0),
  pack_cost_idr bigint NOT NULL CHECK (pack_cost_idr >= 0),
  minimum_packs integer NOT NULL DEFAULT 1 CHECK (minimum_packs > 0),
  capacity_packs integer CHECK (capacity_packs IS NULL OR capacity_packs >= 0),
  active boolean NOT NULL DEFAULT true,
  UNIQUE (supplier_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS inventory_sale (
  id uuid PRIMARY KEY,
  source text NOT NULL CHECK (source IN ('POS_SIMULATOR', 'POS_CASHIER', 'IMPORT')),
  occurred_at timestamptz NOT NULL,
  business_date date NOT NULL,
  status text NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('COMPLETED', 'VOIDED')),
  currency text NOT NULL DEFAULT 'IDR' CHECK (currency = 'IDR'),
  total_amount_idr bigint NOT NULL CHECK (total_amount_idr >= 0),
  total_items integer NOT NULL CHECK (total_items > 0),
  voided_at timestamptz,
  void_reason text
);
CREATE INDEX IF NOT EXISTS inventory_sale_business_date_idx ON inventory_sale(business_date, occurred_at DESC);
CREATE TABLE IF NOT EXISTS inventory_sale_item (
  sale_id uuid NOT NULL REFERENCES inventory_sale(id),
  product_id text NOT NULL REFERENCES inventory_product(id),
  product_name text NOT NULL,
  quantity integer NOT NULL CHECK (quantity > 0),
  unit_price_idr bigint NOT NULL CHECK (unit_price_idr >= 0),
  subtotal_idr bigint NOT NULL CHECK (subtotal_idr >= 0),
  PRIMARY KEY (sale_id, product_id)
);
CREATE TABLE IF NOT EXISTS inventory_stock_movement (
  id uuid PRIMARY KEY,
  ingredient_id text NOT NULL REFERENCES inventory_ingredient(id),
  movement_type text NOT NULL CHECK (movement_type IN ('SALE', 'STOCK_IN', 'ADJUSTMENT', 'WASTE', 'DAMAGE')),
  quantity_change_base bigint NOT NULL,
  transaction_id uuid REFERENCES inventory_sale(id),
  recommendation_id uuid,
  external_receipt_id text,
  reference_id text NOT NULL,
  note text,
  occurred_at timestamptz NOT NULL,
  business_date date NOT NULL,
  inventory_version bigint NOT NULL,
  CHECK (quantity_change_base <> 0 OR movement_type = 'ADJUSTMENT'),
  UNIQUE (external_receipt_id)
);
CREATE INDEX IF NOT EXISTS inventory_movement_ingredient_idx ON inventory_stock_movement(ingredient_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS inventory_movement_type_idx ON inventory_stock_movement(movement_type, occurred_at DESC);

CREATE TABLE IF NOT EXISTS inventory_forecast_run (
  id uuid PRIMARY KEY,
  as_of_date date NOT NULL,
  generated_at timestamptz NOT NULL,
  model_name text NOT NULL,
  model_version text NOT NULL,
  source text NOT NULL CHECK (source IN ('XGBOOST', 'FALLBACK')),
  is_synthetic boolean NOT NULL,
  fallback_reason text,
  data_cutoff timestamptz NOT NULL,
  inventory_version bigint NOT NULL,
  forecast_version bigint NOT NULL UNIQUE,
  UNIQUE (as_of_date, model_version, source)
);
CREATE TABLE IF NOT EXISTS inventory_forecast_item (
  run_id uuid NOT NULL REFERENCES inventory_forecast_run(id),
  product_id text NOT NULL REFERENCES inventory_product(id),
  horizon smallint NOT NULL CHECK (horizon BETWEEN 1 AND 3),
  forecast_date date NOT NULL,
  predicted_demand integer NOT NULL CHECK (predicted_demand >= 0),
  PRIMARY KEY (run_id, product_id, horizon)
);

CREATE TABLE IF NOT EXISTS inventory_procurement_plan (
  id uuid PRIMARY KEY,
  forecast_run_id uuid NOT NULL REFERENCES inventory_forecast_run(id),
  generated_at timestamptz NOT NULL,
  inventory_version bigint NOT NULL,
  forecast_version bigint NOT NULL,
  supplier_version bigint NOT NULL,
  budget_idr bigint NOT NULL CHECK (budget_idr >= 0),
  total_estimated_cost_idr bigint NOT NULL CHECK (total_estimated_cost_idr >= 0),
  optimizer_status text NOT NULL CHECK (optimizer_status IN ('OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'ERROR')),
  plan_outcome text NOT NULL CHECK (plan_outcome IN ('COMPLETE', 'PARTIAL', 'INFEASIBLE')),
  solver_status_detail text NOT NULL,
  risk_snapshot jsonb NOT NULL,
  unmet_requirements jsonb NOT NULL,
  limitations jsonb NOT NULL DEFAULT '[]'::jsonb,
  input_fingerprint text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS inventory_recommendation (
  id uuid PRIMARY KEY,
  plan_id uuid NOT NULL REFERENCES inventory_procurement_plan(id),
  ingredient_id text NOT NULL REFERENCES inventory_ingredient(id),
  supplier_id text NOT NULL REFERENCES inventory_supplier(id),
  offer_id text NOT NULL REFERENCES inventory_supplier_offer(id),
  recommended_quantity_base bigint NOT NULL CHECK (recommended_quantity_base > 0),
  received_quantity_base bigint NOT NULL DEFAULT 0 CHECK (received_quantity_base >= 0),
  packs integer NOT NULL CHECK (packs > 0),
  estimated_cost_idr bigint NOT NULL CHECK (estimated_cost_idr >= 0),
  recommended_order_date date NOT NULL,
  expected_arrival_at timestamptz NOT NULL,
  unmet_quantity_base bigint NOT NULL DEFAULT 0 CHECK (unmet_quantity_base >= 0),
  reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
  reviewed_at timestamptz,
  explanation_text text NOT NULL,
  explanation_source text NOT NULL CHECK (explanation_source IN ('QWEN', 'FALLBACK')),
  UNIQUE (plan_id, ingredient_id)
);
ALTER TABLE inventory_stock_movement DROP CONSTRAINT IF EXISTS inventory_stock_movement_recommendation_id_fkey;
ALTER TABLE inventory_stock_movement ADD CONSTRAINT inventory_stock_movement_recommendation_id_fkey
  FOREIGN KEY (recommendation_id) REFERENCES inventory_recommendation(id);

CREATE TABLE IF NOT EXISTS inventory_idempotency (
  action text NOT NULL,
  key text NOT NULL,
  request_hash text NOT NULL,
  status_code integer NOT NULL,
  response_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (action, key)
);

-- month_start is the first calendar date of the event's Asia/Jakarta month.
CREATE TABLE IF NOT EXISTS inventory_activity_log (
  id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  business_date date NOT NULL,
  month_start date NOT NULL,
  actor text NOT NULL,
  source text NOT NULL,
  correlation_id text NOT NULL,
  action text NOT NULL,
  entity_type text NOT NULL,
  entity_id text NOT NULL,
  success boolean NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (month_start, id)
) PARTITION BY RANGE (month_start);
CREATE INDEX IF NOT EXISTS inventory_activity_time_idx ON inventory_activity_log(month_start, occurred_at DESC);
CREATE INDEX IF NOT EXISTS inventory_activity_entity_idx ON inventory_activity_log(month_start, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS inventory_activity_action_idx ON inventory_activity_log(month_start, action, occurred_at DESC);
