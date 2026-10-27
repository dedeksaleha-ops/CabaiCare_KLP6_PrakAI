"""Perhitungan rekomendasi dosis pupuk dari status hara dan fase pertumbuhan."""

NUTRIENT_NAME = {"N": "Nitrogen (N)", "P2O5": "Fosfor (P2O5)", "K2O": "Kalium (K2O)"}
NUTRIENT_DEF = {"N": "def_N", "P2O5": "def_P", "K2O": "def_K"}
COL_SEASON = "Dosis musiman (kg hara/ha)"
COL_BASAL = "Pupuk dasar (kg hara/ha)"
COL_TOPDRESS = "Susulan per aplikasi (kg hara/ha)"
COL_PRODUCT = "Produk"
COL_PRODUCT_HA = "Susulan (kg produk/ha)"


def hitung_rekomendasi(kb, wm, fase: str, luas_m2: float) -> dict:
    """Hitung dosis pupuk dasar dan susulan.

    Dosis musiman N-P2O5-K2O dari S4/S5; jadwal pupuk dasar dan susulan 1/3 dari S5.
    Faktor penyesuaian defisiensi/kelebihan N adalah heuristik (lihat catatan di knowledge base).
    """
    if fase not in ("vegetatif", "generatif"):
        raise ValueError("fase harus 'vegetatif' atau 'generatif'")
    if luas_m2 <= 0:
        raise ValueError("luas lahan harus > 0")
    cfg = kb.dose
    ha = luas_m2 / 10000.0
    min_cf = cfg["cf_minimum_penyesuaian"]
    n_app = cfg["jumlah_susulan"]
    col_area = f"Susulan untuk {luas_m2:,.0f} m2 (kg produk)"
    rows, notes = [], []
    for nut, season in cfg["dasar_musiman_per_ha"].items():
        basal_share = cfg["porsi_pupuk_dasar"][nut]
        basal = season * basal_share
        per_app = season * (1 - basal_share) / n_app
        note = "sesuai jadwal S5"
        deficient = wm.get(NUTRIENT_DEF[nut]) >= min_cf
        if deficient:
            per_app = (per_app or season / n_app) * cfg["faktor_defisiensi"]
            note = f"dinaikkan x{cfg['faktor_defisiensi']} karena indikasi defisiensi (heuristik)"
        if nut == "N" and wm.get("exc_N") >= min_cf:
            per_app *= cfg["faktor_kelebihan_N"]
            note = f"dikurangi x{cfg['faktor_kelebihan_N']} karena indikasi kelebihan N (heuristik)"
        prod = cfg["produk"][nut]
        kg_ha = per_app / prod["kadar"]
        rows.append({"Hara": NUTRIENT_NAME[nut], COL_SEASON: round(season, 1), COL_BASAL: round(basal, 1),
                     COL_TOPDRESS: round(per_app, 1), COL_PRODUCT: prod["nama"],
                     COL_PRODUCT_HA: round(kg_ha, 1), col_area: round(kg_ha * ha, 2), "Catatan": note})
        if basal:
            notes.append(f"Pupuk dasar {prod['nama']}: {basal / prod['kadar']:.0f} kg/ha, "
                         f"yaitu {basal / prod['kadar'] * ha:,.1f} kg untuk {luas_m2:,.0f} m2 (diberikan sebelum tanam).")
    notes.append(f"Pupuk kandang dasar: {cfg['pupuk_kandang_t_per_ha']} t/ha (S4, S5).")
    notes.append(cfg["catatan_jadwal"])
    if fase == "vegetatif":
        notes.append("Fase vegetatif: pastikan pupuk dasar sudah diberikan, lalu lanjutkan N dan K susulan sesuai jadwal.")
    else:
        notes.append("Fase generatif: pupuk dasar seharusnya sudah diberikan sebelum tanam; lanjutkan susulan sesuai jadwal dan jangan memberi N berlebih.")
    notes.append(f"Batas total per hara selama musim: jangan melebihi {cfg['batas_atas_musiman']} kg/ha (S5: dosis lebih tinggi tidak menambah hasil).")
    notes.append(cfg["catatan_faktor"])
    notes.append(cfg["pembanding"])
    return {"fase": fase, "luas_m2": luas_m2, "baris": rows, "catatan": notes}
