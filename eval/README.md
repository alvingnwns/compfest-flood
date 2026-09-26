# ARUNA — Phase I Baseline Evaluation Suite

## Tujuan

Suite ini mengukur **baseline** sistem ARUNA sebelum perbaikan (Hackathon Phase I, COMPFEST 18 AIC Babak Final). Hasilnya menjadi titik pembanding kuantitatif untuk iterasi berikutnya. Suite tidak mengubah satu baris pun kode di `be/` atau `fe/`. Seluruh kode evaluasi ada di `eval/`.

## Metodologi

1. **End-to-end via HTTP.** Setiap kasus memanggil API sungguhan lewat `fastapi.testclient.TestClient` terhadap `app.main:app`:
   `POST /api/business-data/import` → `POST /api/simulations` → `GET /disruption` → `POST /recovery` → `GET /recovery` → `GET /impact`.
   Respons 4xx/5xx dicatat sebagai **hasil** kasus, bukan sebagai crash runner.
2. **Workbook uji dibangun secara programmatic.** Data nominal diambil dari `ARUNA_Dummy_Company_Test_Data.xlsx` (15 produk, 20 order, 2 warehouse, 5 store, 2 supplier). Kalau file tidak ada, dipakai salinan hardcoded di `eval/workbook.py`. Mutasi per kasus diterapkan ke data, lalu workbook `.xlsx` baru ditulis dengan openpyxl.
3. **Constraint checker dengan internal inspection** (`eval/checker.py`). KPI bawaan ARUNA tidak menghitung pelanggaran constraint, jadi runner memeriksa ulang setiap plan (baseline dan recovery). Logika pengecekan ditulis ulang dan tidak meng-import kode solver. Namun inputnya **bukan murni black-box**: outcome per order dan produksi dibaca langsung dari state internal backend (lihat [Batasan checker](#batasan-checker)).

Justifikasi: rulebook 2.7 poin 1 untuk sistem optimasi meminta pengujian **kelayakan constraint**, **sensitivitas**, dan **perilaku pada input tidak layak**. C1/C4 menguji kelayakan, C5 menguji sensitivitas, dan C2/C3/C6 menguji input tidak layak.

### Aturan yang dicek (per plan)

| Rule | Isi |
|---|---|
| `order-coverage`, `order-known`, `requested-matches-source` | Setiap order di workbook punya tepat satu outcome dengan quantity yang sama. |
| `allocated-within-requested` | 0 ≤ allocated ≤ requested. |
| `critical-fully-allocated` | Order `critical` dialokasi penuh (plan ready/partial). |
| `assignment-complete` | Order teralokasi punya warehouse, vehicle, dan route. |
| `allocation-lines-sum` | Jumlah baris alokasi per produk = allocated. |
| `substitution-allowed` | Produk teralokasi ≠ produk diminta hanya jika `allowSubstitution=true`. |
| `vehicle-available`, `vehicle-capacity` | Vehicle ada, available, dan total muatan ≤ `capacityUnits` (setelah override). |
| `warehouse-inventory` | Untuk tiap produk p: Σ_w max(0, allocated(w,p) − inventory(w,p)) ≤ production(p). |
| `factory-capacity` | Total produksi ≤ kapasitas pabrik. |
| `route-known`, `route-matches-order` | Route ada di hasil `/disruption` dan menghubungkan warehouse terpilih → store order. |
| `no-critical-route` (recovery) | `floodExposure` route (dibaca dari `/disruption`, bukan dari outcome) ≠ `critical`. |
| `baseline-preferred-warehouse` (baseline) | Plan baseline hanya memakai preferred warehouse store tersebut. |

### Batasan checker

**Sumber data (internal inspection).**

- `baselineOrderOutcomes`, `recoveryOrderOutcomes`, dan data produksi ditandai `exclude=True` di `RecoveryResult`, jadi tidak muncul di respons HTTP. Runner membacanya secara read-only dari `simulation_repository`, yang berjalan di proses yang sama dengan TestClient.
- Akibatnya checker **tidak bisa dijalankan terhadap server yang sudah di-deploy**. Checker juga bergantung pada struktur internal repository tersebut.
- Alokasi per produk plan recovery diambil dari `commerceActions` di respons HTTP. Vehicle dan kapasitas pabrik berasal dari `GET /api/scenarios/historical-jakarta`, dan route berasal dari `GET /disruption`.
- Beberapa aturan **meniru logika aplikasi**, bukan diturunkan secara independen:
  - efek `vehicleOverrides` pada kapasitas;
  - aturan preferred warehouse per store saat import;
  - asumsi bahwa plan baseline tidak memakai substitusi, karena alokasi per produk baseline tidak dipublikasikan.

**Yang tidak dicek.**

- Konsumsi material/BOM terhadap ketersediaan supplier, termasuk faktor pengurangan supplier akibat banjir.
- Batas `maxAdditionalDelayMinutes`, serta kebenaran ETA, deadline, dan delay.
- Kebenaran aritmetika KPI dari `/impact`.
- Optimalitas solusi: checker hanya menilai kelayakan (feasibility).
- Distribusi produksi per warehouse. `warehouse-inventory` hanya memakai kondisi agregat per produk yang ekuivalen dengan kelayakan.

**Cakupan.**

- Jika solver **tidak menghasilkan plan** (C2), tidak ada outcome untuk dicek, sehingga checker mencatat 0 check. Ini berarti "tidak dievaluasi", **bukan** "0 pelanggaran".
- Checkpoint-1 hanya mencakup satu dataset (workbook dummy) dan tiga kasus.
- Sanity check manual: checker berhasil menangkap enam jenis pelanggaran yang sengaja disuntikkan ke plan buatan (kapasitas vehicle, kapasitas pabrik, inventory, route critical, substitusi, order critical). Uji ini belum menjadi bagian dari suite.

## Kasus uji

| ID | Nama | Mutasi | Ekspektasi (kriteria PASS) | Alasan pemilihan | Status |
|---|---|---|---|---|---|
| C1 | nominal-baseline | Data apa adanya, rainfall Q2 | status ready/partial **dan** 0 violation; catat semua KPI | Titik acuan performa pada kondisi normal | ✅ checkpoint-1 |
| C2 | critical-order-infeasible | quantity ORDER-001 (critical) ×10 | status **harus** `no-feasible-plan` | Menguji perilaku hard constraint pada input mustahil | ✅ checkpoint-1 |
| C3 | deadline-impossible | Semua `deadlineMinutes` = 5 | Observasi order yang masih teralokasi; degradasi besar | Input tidak layak pada dimensi waktu | ⏳ belum |
| C4 | vehicle-capacity-crunch | `vehicleOverrides` capacity 30 | Fulfillment turun, 0 pelanggaran kapasitas | Kelayakan constraint di bawah tekanan kapasitas | ⏳ belum |
| C5 | hazard-sensitivity | Data sama, Q1 vs Q4 (dua simulasi) | Kedua run ready/partial dengan 0 violation; delta KPI terdokumentasi | Sensitivitas output terhadap skenario hazard | ✅ checkpoint-1 |
| C6 | import-negative | Dua workbook terpisah (lihat di bawah) | Kedua import ditolak 422 dengan kode error yang sesuai | Validasi input di batas sistem | ⏳ belum |

**Rencana C6: dua workbook terpisah.** Parser (`be/app/business_import/parser.py`) berhenti setelah menemukan sheet yang hilang dan tidak lanjut memindai formula. Jadi satu workbook yang sekaligus tanpa BOM dan berisi formula hanya akan menghasilkan `MISSING_SHEET`. Karena itu C6 dipecah menjadi dua sub-kasus:

- **C6a (missing-sheet):** workbook nominal tanpa sheet `BOM`. Ekspektasi: 422 `BUSINESS_DATA_VALIDATION_FAILED`, dan `details.errors` memuat `code=MISSING_SHEET` dengan `sheet=BOM`.
- **C6b (formula-cell):** workbook nominal lengkap, tetapi satu sel diisi formula (misalnya `Orders.quantity` = `=100+80`). Ekspektasi: 422, dan `details.errors` memuat `code=FORMULA_NOT_ALLOWED` pada sheet/baris/kolom sel tersebut.

## Metrik

Metrik dibagi dua dan **tidak boleh digabung**:

**1. Kesesuaian ekspektasi (correctness).** Apakah sistem berperilaku sesuai spesifikasi kasus uji.

- **Skor ekspektasi** = jumlah kasus yang sesuai ekspektasi / total kasus yang dijalankan.
- **Constraint Violation Rate** (↓) = jumlah pelanggaran / jumlah check yang dievaluasi.

Skor ekspektasi yang tinggi **bukan** berarti performa bisnis tinggi. Contohnya C2: kasus ini PASS justru karena sistem menolak membuat plan.

**2. Tiga KPI performa.** Seberapa baik plan yang dihasilkan. Hanya dihitung untuk kasus yang benar-benar menghasilkan plan.

| KPI | Arah | Definisi |
|---|---|---|
| Service Level | ↑ | `orders-fulfilled` / total order (order dihitung fulfilled bila allocated = requested) |
| Unfulfilled Demand | ↓ | Σ requested − Σ allocated (unit) |
| Operational Loss | ↓ | KPI `sales-exposure-risk` (IDR) |

## Cara menjalankan

Dari root repo, pakai interpreter backend (Python ≥ 3.12 dengan dependency `be/requirements.txt`):

```bash
be/.venv/Scripts/python.exe -m eval.run_eval      # Windows
be/.venv/bin/python -m eval.run_eval              # Linux/macOS
```

Output:

- tabel ringkas + findings di stdout;
- `eval/results/baseline_YYYYMMDD_HHMMSS.json` berisi per kasus: `case_id`, `expectation`, `passed`, `actual_status`, `kpis` (baseline vs recovery), `outcome_metrics`, `constraint_violations`, `constraint_checks` (per rule + detail pelanggaran), `not_fully_fulfilled`, dan `findings`.

`eval/results/` di-gitignore. Hasil run baru tidak otomatis ikut version control. Baseline resmi ditambahkan secara eksplisit dengan `git add -f eval/results/<file>.json`.

## BASELINE FINDINGS

Run pertama checkpoint-1 disimpan di `eval/results/baseline_20260926_101319.json` (2026-09-26, data `ARUNA_Dummy_Company_Test_Data.xlsx`, kode aplikasi di commit `a61268f`). Run kedua menghasilkan status, KPI, dan hasil checker yang identik (deterministik).

Run 10:20 (`eval/results/baseline_20260926_102041.json`) tersedia di repo sebagai bukti determinisme; hasilnya identik dengan canonical run 10:13.

Catatan: string `findings` di JSON run pertama masih memakai redaksi awal untuk C2 ("20/20 gagal total", sales exposure). Interpretasi yang berlaku adalah redaksi di bawah ini: **C2 = no plan produced**.

### 1. Kesesuaian ekspektasi: 3/3

| Kasus | Ekspektasi | Hasil | Check dievaluasi | Pelanggaran |
|---|---|---|---|---|
| C1 (Q2) | ready/partial, 0 violation | `partial` ✅ | 238 baseline + 245 recovery | 0 |
| C2 (Q2) | `no-feasible-plan` | `no-feasible-plan` ✅ | 0 (tidak ada plan) | tidak dievaluasi |
| C5 (Q1, Q4) | ready/partial, 0 violation | `partial`, `partial` ✅ | 238 + 245 (Q1), 238 + 231 (Q4) | 0 |

### 2. Tiga KPI performa (hanya kasus yang menghasilkan plan)

| Kasus | Plan | Service Level ↑ | Unfulfilled Demand ↓ (unit) | Operational Loss ↓ (IDR) |
|---|---|---|---|---|
| C1 (Q2) | baseline | 7/20 (0,35) | 780 / 2.325 | 39.500.000 |
| C1 (Q2) | recovery | 7/20 (0,35) | 635 / 2.325 | 31.984.000 |
| C5 (Q1) | baseline | 7/20 (0,35) | 780 / 2.325 | 39.500.000 |
| C5 (Q1) | recovery | 8/20 (0,40) | 635 / 2.325 | 32.205.000 |
| C5 (Q4) | baseline | 7/20 (0,35) | 780 / 2.325 | 39.840.000 |
| C5 (Q4) | recovery | 8/20 (0,40) | 780 / 2.325 | 38.755.000 |

C2 tidak masuk tabel ini. Tidak ada plan yang dihasilkan, sehingga tidak ada kinerja yang bisa diukur.

### 3. Kelemahan yang ditemukan

1. **C2 — no plan produced.** Satu order critical dibuat mustahil: 1.800 unit, sedangkan kendaraan terbesar 800 unit dan satu order hanya boleh memakai satu kendaraan. Akibatnya solver tidak menghasilkan plan sama sekali, baik baseline maupun recovery (`no-feasible-plan`). Tidak ada plan parsial untuk 19 order lain yang sebenarnya bisa dilayani.
   - Angka yang dilaporkan `/impact` untuk kasus ini (0/20 fulfilled, sales exposure IDR 224.070.000) adalah **artefak dari 0 alokasi**. Angka itu **bukan** kerugian aktual dan **bukan** 20 order yang teramati gagal.
2. **Diagnostik infeasibility minim (C2).** Endpoint recovery tetap mengembalikan 201. `error.details` hanya berisi kebijakan umum (`criticalOrderPolicy`), tanpa menyebut order atau constraint penyebabnya.
3. **Fulfillment penuh rendah pada data nominal (C1).**
   - Hanya 7/20 order terpenuhi penuh, baik di baseline maupun recovery.
   - Recovery memperbaiki alokasi unit (unfulfilled 780 → 635; loss turun ±IDR 7,5 juta), tetapi tidak menambah jumlah order yang terpenuhi penuh.
   - On-time delivery justru turun dari 0,35 ke 0,25, karena route aman lebih lambat (average delay 0 → 0,2 menit).
   - Kapasitas armada (2.050 unit) memang di bawah total demand (2.325 unit).
4. **Sensitivitas hazard (C5).**
   - Relative hazard index naik dari 0,15 (Q1) ke 0,73 (Q4).
   - Di Q4, 4 dari 9 route recovery ber-exposure `critical` sehingga dikeluarkan. Akibatnya failed-orders recovery naik +2, unfulfilled naik 635 → 780 unit, dan operational loss naik +IDR 6,55 juta. Service level tetap 8/20.
   - Plan baseline hampir tidak sensitif terhadap hazard (+IDR 340 ribu), karena baseline tetap boleh memakai route `critical`.
