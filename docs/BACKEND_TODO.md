# ResiliChain AI Backend TODO

Dokumen ini adalah rencana implementasi backend MVP. Functional requirements menjelaskan perilaku produk; [`BACKEND_INTEGRATION_CONTRACT.md`](./BACKEND_INTEGRATION_CONTRACT.md) adalah kontrak API yang wajib dipatuhi agar frontend dapat beralih dari MSW ke FastAPI tanpa perubahan UI.

## Prinsip Implementasi

- Backend menggunakan FastAPI dan berjalan lokal di `http://localhost:8000`.
- MVP bersifat **offline-first**: snapshot bisnis, banjir, jaringan jalan, dan artifact model disimpan lokal.
- JSON API menggunakan camelCase; GeoJSON memakai urutan koordinat `[longitude, latitude]`.
- Risk score adalah probabilitas `0–1`, bukan klaim kepastian banjir.
- Simulasi, rekomendasi, KPI, dan explainability adalah milik backend; frontend hanya menampilkan hasil.
- Jangan mengubah path, enum, unit, atau struktur respons dalam integration contract tanpa perubahan kontrak yang disengaja.

## Target Alur Demo

```text
Pilih historical scenario
  -> POST simulation
  -> road risk + impact + baseline/recovery route
  -> generate recovery plan
  -> recovery actions + explanations
  -> before/after KPI
```

## Phase 0 — Kontrak dan Fondasi Proyek

- [x] Baca dan jadikan [`BACKEND_INTEGRATION_CONTRACT.md`](./BACKEND_INTEGRATION_CONTRACT.md) sebagai source of truth untuk HTTP API.
- [ ] Cocokkan setiap respons FastAPI dengan schema Zod pada `fe/src/domain/`.
- [x] Buat struktur `be/app/`:

  ```text
  app/
  ├─ api/
  ├─ schemas/
  ├─ services/
  ├─ repositories/
  ├─ data/
  ├─ models/
  └─ main.py
  ```

- [x] Tambahkan `requirements.txt` atau `pyproject.toml` yang mem-pin dependency utama: FastAPI, Uvicorn, Pydantic, scikit-learn, NetworkX, OR-Tools, Joblib, dan library test.
- [x] Konfigurasikan CORS untuk `http://localhost:3000`, metode `GET`/`POST`, dan header `Content-Type`/`Accept`.
- [x] Buat error handler yang selalu mengembalikan:

  ```json
  { "code": "...", "message": "...", "retryable": false, "details": {} }
  ```

- [x] Tambahkan health check internal (bukan bagian kontrak frontend) untuk memverifikasi server hidup.

**Selesai bila:** server dapat dijalankan lokal, CORS berfungsi, dan respons error mengikuti envelope kontrak.

## Phase 1 — Snapshot Historical Replay

- [x] Tentukan satu pilot area dan event: Jakarta, 04 Maret 2025.
- [x] Siapkan snapshot bisnis lokal yang konsisten:
  - [x] 1 factory
  - [x] 2 supplier
  - [x] 2 warehouse
  - [x] 2 SKU
  - [x] 3 vehicle
  - [x] 5 outlet/destination
  - [x] Maksimum 20 order
- [x] Pastikan seluruh ID referensial valid: material ke supplier/product, inventory ke facility/product, dan order ke store/product.
- [x] Tambahkan flood extent lokal dalam GeoJSON `Polygon` atau `MultiPolygon`.
- [x] Tambahkan road segment snapshot dengan geometri, panjang/travel time, dan feature risiko yang diperlukan model.
- [x] Sediakan graph jalan lokal untuk routing, sehingga demo tidak membutuhkan OSM/API online.
- [x] Implementasikan `GET /api/scenarios/historical-jakarta`.

**Selesai bila:** endpoint scenario mengembalikan snapshot valid dan dapat digunakan saat internet dimatikan.

## Phase 2 — Lifecycle Simulation dan Contract API Dasar

- [x] Buat repository simulation in-memory untuk MVP.
- [x] Implementasikan `POST /api/simulations` dengan input `{ "scenarioId": "..." }` dan respons `201`.
- [x] Implementasikan `GET /api/simulations/{simulationId}` untuk polling.
- [x] Terapkan lifecycle: `queued`, `processing`, `completed`, `failed`.
- [x] Sertakan `createdAt`, `completedAt`, `modelVersion`, `optimizerVersion`, `dataMode`, dan `historicalDataStatus` sesuai state contract.
- [x] Kembalikan `404` untuk simulation atau scenario yang tidak ada, `422` untuk input valid secara JSON tetapi tidak valid secara semantik, dan `409` untuk konflik state.
- [x] Gunakan ID simulation stabil dan timestamp ISO-8601 UTC.

**Selesai bila:** frontend dapat membuat simulation lalu polling hingga `completed`, meskipun engine awal masih sederhana.

## Phase 3 — Model Flood Disruption Risk

- [x] Buat dataset road-level dengan feature minimum: rainfall/historical exposure, hazard, elevation/context, road type/length, dan label disruption.
- [x] Dokumentasikan asal data dan asumsi synthetic/historical untuk setiap feature.
- [x] Latih minimal satu model nyata (baseline Logistic Regression).
- [x] Evaluasi dan simpan precision, recall, F1-score, ROC-AUC; beri perhatian khusus pada recall high-risk.
- [x] Simpan artifact model dengan Joblib beserta version dan metadata evaluasi.
- [x] Implementasikan service inference yang menghasilkan setiap road segment:
  - [x] `riskProbability` dari `0` sampai `1`
  - [x] `riskLevel`: `low | medium | high | critical`
  - [x] `estimatedDelayMinutes` opsional
  - [x] `riskFactors` yang dapat dibaca user
- [x] Jalankan inference ini dari orchestration simulation, bukan sebagai endpoint publik baru.

**Selesai bila:** setiap road segment relevan memiliki skor model dan model artifact/evaluation report dapat direproduksi.

## Phase 4 — Impact Detection dan Risk-Aware Routing

- [x] Definisikan threshold atau penalty risiko yang terdokumentasi untuk routing.
- [x] Implementasikan baseline shortest path menggunakan distance/travel time normal.
- [x] Implementasikan recovery path menggunakan bobot travel time + flood-risk penalty.
- [x] Hindari/exclude ruas di atas threshold risiko tinggi bila rute feasible tersedia.
- [x] Keluarkan baseline dan recovery route sebagai GeoJSON `LineString`/`MultiLineString`.
- [x] Bangun impact engine yang memetakan road risk ke supplier, warehouse, route, dan order terdampak.
- [x] Hitung `roadSegmentsAtRisk`, `salesExposure`, serta issues berisi severity dan deskripsi.
- [x] Implementasikan `GET /api/simulations/{simulationId}/disruption`.
- [x] Kembalikan `409` jika simulation belum `completed`.

**Selesai bila:** peta frontend dapat menampilkan flood extent, ruas berisiko, facility, baseline route, recovery route, dan impact yang koheren.

## Phase 5 — Recovery Optimizer

- [x] Definisikan objective: minimalkan failed orders, delay, dan tambahan biaya transport.
- [x] Terapkan constraint: inventory, material/BOM, kapasitas produksi, kapasitas kendaraan, demand order, deadline, dan availability/risk route.
- [x] Implementasikan keputusan manufacturing: adjusted production quantity/prioritas produk.
- [x] Implementasikan keputusan logistics: warehouse origin, vehicle allocation, dan recovery route.
- [x] Implementasikan keputusan commerce: fulfill, split, delay, substitute, atau prioritize.
- [x] Gunakan OR-Tools untuk model keputusan; hasil harus deterministik untuk input snapshot sama.
- [x] Tangani kondisi `partial` dan `no-feasible-plan` dengan alasan yang jelas.
- [x] Hasilkan untuk setiap keputusan penting: `what`, `why`, dan `expectedImpact`.

**Selesai bila:** demo scenario mengubah minimal satu keputusan manufacturing, logistics, dan commerce tanpa melanggar constraint utama.

## Phase 6 — Recovery dan KPI Endpoints

- [x] Implementasikan `POST /api/simulations/{simulationId}/recovery` dengan constraints opsional:

  ```json
  {
    "constraints": {
      "allowSubstitution": true,
      "maxAdditionalDelayMinutes": 60
    }
  }
  ```

- [x] Implementasikan `GET /api/simulations/{simulationId}/recovery` untuk polling state `queued`, `processing`, `ready`, `partial`, `no-feasible-plan`, atau `failed`.
- [x] Cegah generation bersamaan menggunakan `409`.
- [x] Hitung KPI berdasarkan output optimizer, bukan angka UI/hardcoded:
  - [x] `orders-fulfilled`
  - [x] `on-time-delivery`
  - [x] `failed-orders`
  - [x] `average-delay`
  - [x] `sales-exposure-risk`
- [x] Implementasikan `GET /api/simulations/{simulationId}/impact` beserta `actionCounts`.
- [x] Kembalikan `409` bila recovery belum selesai saat impact diminta.

**Selesai bila:** plan recovery dan before/after KPI valid serta semua count konsisten dengan hasil optimizer.

## Phase 7 — Testing dan Validasi Kontrak

- [x] Unit test: risk classification, impact mapping, route penalty, optimizer constraint, KPI calculation.
- [x] API test: happy path, malformed input (`400`), missing resource (`404`), invalid state (`409`), semantic input invalid (`422`).
- [x] Contract test tiap endpoint terhadap fixture yang ekuivalen dengan Zod frontend.
- [x] Test referential integrity seluruh data snapshot.
- [x] Test offline: jalankan simulation saat koneksi eksternal tidak tersedia.
- [x] Test reproducibility: input dan artifact sama menghasilkan output sama.
- [x] Ukur waktu complete simulation; target maksimal 10 detik pada laptop development.

**Selesai bila:** seluruh test lulus dan demo acceptance scenario dalam functional requirements dapat dibuktikan.

## Phase 8 — Integrasi Frontend dan Demo

- [x] Jalankan FastAPI pada port `8000`.
- [x] Buat/ubah `fe/.env.local`:

  ```dotenv
  NEXT_PUBLIC_DATA_SOURCE=api
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  ```

- [x] Restart Next.js setelah perubahan environment.
- [x] Verifikasi flow: Scenario → Simulation → Disruption → Recovery → Impact.
- [x] Pastikan frontend tidak menjalankan MSW saat `NEXT_PUBLIC_DATA_SOURCE=api`.
- [x] Verifikasi CORS dari browser, bukan hanya dari Swagger/curl.
- [x] Siapkan command fresh start dan demo script singkat.

**Selesai bila:** aplikasi berjalan end-to-end menggunakan FastAPI tanpa perubahan komponen frontend.

## Definition of Done MVP

- [x] FR-01 sampai FR-12 terpenuhi.
- [x] Tujuh endpoint contract tersedia dan responsnya kompatibel dengan schema frontend.
- [x] Model flood-risk nyata, model artifact, dan evaluation report tersedia.
- [x] Optimizer menghasilkan plan feasible/partial/no-feasible-plan secara jujur dan explainable.
- [x] Historical replay berjalan offline.
- [x] Tidak ada wording yang menyatakan jalan "pasti banjir"; gunakan probability/risk.
- [x] Demo dapat dimulai ulang dari fresh start tanpa setup manual kompleks.
