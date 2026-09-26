-- Imported historical daily sales that feed forecasting without touching the stock ledger.
-- Idempotent: scripts/migrate_inventory.py re-applies every migration file in order.
SET search_path TO aruna_inventory, public;

CREATE TABLE IF NOT EXISTS inventory_sales_history_batch (
  id uuid PRIMARY KEY,
  imported_at timestamptz NOT NULL,
  source_filename text,
  row_count integer NOT NULL CHECK (row_count > 0),
  day_count integer NOT NULL CHECK (day_count > 0),
  first_date date NOT NULL,
  last_date date NOT NULL,
  content_sha256 text NOT NULL,
  correlation_id text NOT NULL,
  CHECK (first_date <= last_date)
);

-- One row per business date and product. A date present here counts as a recorded day;
-- products absent on a recorded day sold zero.
CREATE TABLE IF NOT EXISTS inventory_sales_history (
  business_date date NOT NULL,
  product_id text NOT NULL REFERENCES inventory_product(id),
  quantity integer NOT NULL CHECK (quantity >= 0),
  batch_id uuid NOT NULL REFERENCES inventory_sales_history_batch(id),
  PRIMARY KEY (business_date, product_id)
);
CREATE INDEX IF NOT EXISTS inventory_sales_history_batch_idx ON inventory_sales_history(batch_id);

-- Forecast runs are reused only for identical history inputs.
ALTER TABLE inventory_forecast_run ADD COLUMN IF NOT EXISTS history_fingerprint text NOT NULL DEFAULT 'legacy';
ALTER TABLE inventory_forecast_run ADD COLUMN IF NOT EXISTS history_covered_days smallint;
ALTER TABLE inventory_forecast_run DROP CONSTRAINT IF EXISTS inventory_forecast_run_as_of_date_model_version_source_key;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'inventory_forecast_run_history_key'
      AND conrelid = 'aruna_inventory.inventory_forecast_run'::regclass
  ) THEN
    ALTER TABLE inventory_forecast_run
      ADD CONSTRAINT inventory_forecast_run_history_key
      UNIQUE (as_of_date, model_version, source, history_fingerprint);
  END IF;
END $$;
