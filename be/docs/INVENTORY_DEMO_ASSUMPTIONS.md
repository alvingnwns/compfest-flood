# Inventory demo assumptions

These values make the single-outlet Product Track flow demonstrable. They are approved engineering assumptions, not measured facts about the target business.

## Catalog and recipes

- Product IDs and names come from `be/data/new_data/aruna_juice.csv`.
- Every menu has one primary fruit ingredient.
- The fixed recipe uses `0.25 kg` fruit per cup, within the stated `200–400 g` assumption range.
- Demo selling price is `IDR 20,000` per cup for every menu until the owner provides a real catalog.
- Water, sugar, ice, packaging, yield loss, and substitutions are outside this initial recipe. The API must not imply they are modeled.

## Inventory policy

- Fruit display/storage unit: `kg`; internal quantity unit: milligram.
- Opening system stock: `10 kg` per fruit.
- Safety stock: `3 kg` per fruit.
- Reorder point: `5 kg` per fruit.
- Storage capacity: `50 kg` per fruit.
- Opening balances are auditable `ADJUSTMENT` ledger movements.

## Supplier policy

- One demo supplier is available for all fruit ingredients.
- Lead time: `24 hours`.
- Pack size: `5 kg`.
- MOQ: one pack.
- Capacity: ten packs per ingredient per recommendation run.
- Demo pack cost: `IDR 100,000`.
- These values are optimizer inputs, not historical supplier evidence.

## Modeling limits

- The supplied dataset is synthetic POS-like demand with generator version `aruna-juice-v4.0`.
- Training targets represent synthetic unconstrained demand.
- Runtime POS history is fulfilled sales and can be censored by stockouts.
- No measured expiry/lot data exists, so the backend does not claim quantified waste reduction.
