# ARUNA inventory seed

CSV seed untuk MVP juice. Harga menu berasal dari gambar menu yang diberikan pengguna. BOM, stok awal, supplier, biaya bahan, kapasitas, MOQ, order multiple, shelf life, budget, dan lead time adalah asumsi sintetis untuk demo dan development.

- `menus.csv`: harga menu.
- `recipes_bom.csv`: kebutuhan bahan untuk satu cup.
- `ingredients_inventory.csv`: master bahan, stok awal, biaya, kapasitas, dan shelf life.
- `suppliers.csv`: penawaran supplier, MOQ, kelipatan order, kapasitas per hari, dan lead time.
- `procurement_config.csv`: constraint global optimizer.

Semua tanggal dan batas hari/bulan bisnis menggunakan Asia/Jakarta. `SUP-FRUIT` memiliki kapasitas tambahan gabungan 60 kg/hari yang belum dapat direpresentasikan oleh satu baris per bahan; backend harus menerapkan constraint grup supplier tersebut selain `supply_capacity_per_day=20` per bahan.
