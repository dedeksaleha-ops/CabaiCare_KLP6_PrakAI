"""Layanan konsultasi: validasi input dan penyusunan hasil dari working memory."""
import uuid
from datetime import datetime

from .explanation import explain_how
from .recommender import hitung_rekomendasi


def validate_input(kb, selected: dict, luas_m2: float):
    """Validasi input formulir. Mengembalikan (errors, warnings)."""
    errors, warnings = [], []
    if not selected:
        errors.append("Pilih minimal satu gejala yang teramati.")
    if luas_m2 is None or luas_m2 <= 0:
        errors.append("Luas lahan harus lebih dari 0 m2.")
    for fid in selected:
        if fid not in kb.facts:
            errors.append(f"Gejala {fid} tidak dikenal.")
    for a, b in kb.conflicts:
        if a in selected and b in selected:
            warnings.append(f"Gejala '{kb.name_of(a)}' dan '{kb.name_of(b)}' jarang muncul bersamaan; periksa kembali pengamatan.")
    return errors, warnings


def set_phase(wm, fase: str):
    """Masukkan fakta konteks fase ke working memory."""
    wm.set_user_fact("FASE_VEG", 1.0 if fase == "vegetatif" else 0.0)
    wm.set_user_fact("FASE_GEN", 1.0 if fase == "generatif" else 0.0)


def build_result(kb, wm, mode: str, fase: str, luas_m2: float, trace: list, threshold: float = 0.2) -> dict:
    """Susun hasil konsultasi (dict yang bisa diserialisasi ke JSON)."""
    def collect(tipe):
        items = [{"id": c, "name": v["name"], "cf": round(wm.get(c), 4)}
                 for c, v in kb.conclusions_of_type(tipe).items() if wm.get(c) >= threshold]
        return sorted(items, key=lambda x: -x["cf"])

    diagnosis, saran = collect("diagnosis"), collect("saran")
    rek = hitung_rekomendasi(kb, wm, fase, luas_m2)
    how = {d["id"]: explain_how(kb, wm, d["id"]) for d in diagnosis + saran}
    return {
        "id": uuid.uuid4().hex[:8],
        "waktu": datetime.now().isoformat(timespec="seconds"),
        "mode": mode, "fase": fase, "luas_m2": luas_m2,
        "input": {k: v for k, v in wm.user_facts.items() if not k.startswith("FASE_")},
        "diagnosis": diagnosis, "saran": saran, "dosis": rek,
        "aturan_dipakai": list(wm.fired), "how": how,
        "trace": [t["text"] for t in trace],
        "memori_log": list(wm.history),
    }
