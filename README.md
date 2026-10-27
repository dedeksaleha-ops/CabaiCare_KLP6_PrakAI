# Sistem Pakar Rekomendasi Pemupukan Cabai (Rule-Based, Python)

UTS Praktikum INF313 Kecerdasan Artifisial, Kelompok 6, tema 7: rekomendasi jenis dan dosis pupuk tanaman cabai
berdasarkan fase pertumbuhan (vegetatif/generatif) dan gejala visual kekurangan atau kelebihan unsur hara.

## Fitur
| Rubrik | Implementasi |
|---|---|
| Knowledge Base | `data/knowledge_base.json`: 31 aturan IF-THEN (faktual + heuristik), tiap aturan punya CF dan sumber |
| Inference Engine | Forward chaining (urut level) dan backward chaining (goal-driven, bertanya ke pengguna) di `expert/inference.py`; trace langkah demi langkah |
| Working Memory | `expert/working_memory.py`: fakta pengguna, hasil inferensi, derivasi, log perubahan |
| User Interface | Streamlit (`app.py`, `ui/`): formulir gejala, validasi, tabel hasil, tingkat kepercayaan |
| Explanation | WHY (alasan pertanyaan, backward + tooltip di form) dan HOW (rantai penalaran + aturan terpakai) |
| Certainty Factor | CF aturan x min(CF premis); gabungan `CF = a + b(1-a)`; CF input pengguna 0.4 / 0.6 / 0.8 / 1.0 |
| Knowledge Acquisition | Tab "Basis Pengetahuan": tambah/ubah/hapus aturan, validasi, simpan ke JSON, pulihkan versi awal |
| Reporting & Logging | Ekspor TXT/CSV/PDF, riwayat `data/history.json`, statistik, frekuensi aturan |
| Pencarian & Filter | Cari gejala, filter riwayat (diagnosis, fase, CF, tanggal), database kondisi hara |

## Instalasi dan menjalankan
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest -q                                           # 16 pengujian otomatis
```

## Struktur
```
app.py                  # entry point Streamlit
expert/                 # logika sistem pakar (tanpa dependensi UI)
  certainty.py  models.py  working_memory.py  knowledge_base.py
  inference.py  explanation.py  recommender.py  consultation.py  reporting.py
ui/                     # tab antarmuka
data/                   # knowledge_base.json (+ .default.json), history.json (dibuat otomatis)
tests/test_system.py
```

## Alur pengetahuan
Gejala (16 gejala, G01-G17) -> status hara (`def_N`, `def_P`, `def_K`, `def_Ca`, `def_Mg`, `def_Fe`, `exc_N`) -> saran (bergantung fase) -> dosis.
Dosis musiman cabai N-P2O5-K2O = 150-150-150 kg/ha (S4, S5). Jadwal mengikuti S5: pupuk dasar (pupuk kandang + seluruh P) sebelum tanam, N dan K susulan 1/3 dosis pada 1, 5, 9 minggu setelah tanam.

## Referensi dan status verifikasi
Tujuh sumber khusus cabai atau paprika (*Capsicum annuum*), semuanya dibaca langsung :
S1 Qur'ania dkk. 2023 (J-ICON), S2 Gulo dkk. 2024 (jurnal Tumbuhan, cabai merah, Nias), S3 portal KAU Chilli, S4 leaflet BALITSA-JIRCAS,
S5 Soetiarso dkk. 2006 (J. Hortikultura), S6 SOP Cabe Merah Puslitbang Hortikultura 2014, S7 Hochmuth & Hochmuth (UF/IFAS, paprika).
Rincian "dipakai untuk" dan "batasan" tiap sumber ada di tab "Tentang & Referensi".
- Aturan `faktual`: hubungan gejala-hara didukung sumber. **Nilai CF adalah estimasi perancang**, bukan angka dari sumber.
- Aturan `heuristik`, faktor dosis x1,25 (defisiensi) dan x0,5 (kelebihan N) adalah pertimbangan perancang; validasi ke pakar/penyuluh.
- Sumber paprika (S7) dan portal India (S3) bukan penelitian di Indonesia; S2 meneliti cabai merah di Nias tetapi deskriptif kualitatif dengan rujukan sekunder. dosis S5 dari satu lokasi (andosol Lembang). Angka dosis antar sumber berbeda (S5 vs SOP S6).
- Gejala visual tidak selalu jelas; uji tanah lebih pasti.

## Pengujian (contoh test case untuk laporan)
Lihat `tests/test_system.py`: TC1 defisiensi N vegetatif, TC2 defisiensi K generatif, TC3 kelebihan N + busuk ujung buah
(rantai 3 level), TC4 tanpa diagnosis, TC5 ambang CF, serta uji backward chaining, validasi KB, siklus, rekomendasi, ekspor.
