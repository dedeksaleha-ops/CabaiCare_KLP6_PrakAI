"""Logging riwayat, statistik, pencarian/filter, dan ekspor laporan (TXT/CSV/PDF)."""
import csv
import io
import json
import os
from collections import Counter
from datetime import datetime


def load_history(path: str) -> list:
    """Baca riwayat konsultasi; kembalikan [] jika file belum ada atau rusak."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_consultation(path: str, record: dict):
    """Tambahkan satu konsultasi ke file riwayat (JSON)."""
    history = load_history(path)
    history.append(record)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=1)


def filter_history(history, diagnosis=None, min_cf=0.0, fase=None, date_from=None, date_to=None):
    """Saring riwayat berdasarkan diagnosis, CF minimum, fase dan rentang tanggal."""
    out = []
    for rec in history:
        d = datetime.fromisoformat(rec["waktu"]).date()
        if date_from and d < date_from:
            continue
        if date_to and d > date_to:
            continue
        if fase and rec.get("fase") != fase:
            continue
        diag = rec.get("diagnosis", [])
        if diagnosis and not any(x["id"] == diagnosis and x["cf"] >= min_cf for x in diag):
            continue
        if not diagnosis and min_cf and not any(x["cf"] >= min_cf for x in diag):
            continue
        out.append(rec)
    return out


def compute_stats(history: list) -> dict:
    """Statistik penggunaan: jumlah konsultasi, frekuensi diagnosis, aturan, fase, metode."""
    diag, rules, fase, mode, top_cf = Counter(), Counter(), Counter(), Counter(), []
    for rec in history:
        for d in rec.get("diagnosis", []):
            diag[d["name"]] += 1
        rules.update(rec.get("aturan_dipakai", []))
        fase[rec.get("fase", "?")] += 1
        mode[rec.get("mode", "?")] += 1
        if rec.get("diagnosis"):
            top_cf.append(rec["diagnosis"][0]["cf"])
    return {"total": len(history), "diagnosis": diag, "aturan": rules, "fase": fase, "mode": mode,
            "rata_cf_utama": (sum(top_cf) / len(top_cf)) if top_cf else 0.0}


def history_to_csv(history: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "waktu", "metode", "fase", "luas_m2", "diagnosis_utama", "cf_utama", "aturan_dipakai"])
    for r in history:
        top = r["diagnosis"][0] if r.get("diagnosis") else {"name": "-", "cf": 0}
        w.writerow([r["id"], r["waktu"], r["mode"], r["fase"], r["luas_m2"], top["name"], top["cf"],
                    " ".join(r.get("aturan_dipakai", []))])
    return buf.getvalue()


def result_to_text(kb, rec: dict) -> str:
    """Laporan konsultasi dalam format teks."""
    L = ["LAPORAN KONSULTASI - SISTEM PAKAR PEMUPUKAN CABAI", "=" * 52,
         f"ID: {rec['id']}   Waktu: {rec['waktu']}", f"Metode: {rec['mode']}   Fase: {rec['fase']}   Luas: {rec['luas_m2']:,.0f} m2",
         "", "GEJALA DIINPUT:"]
    for fid, cf in rec["input"].items():
        L.append(f"  - {kb.name_of(fid)} (CF {cf:.2f})")
    L += ["", "HASIL DIAGNOSIS:"]
    if rec["diagnosis"]:
        L += [f"  - {d['name']}: kepercayaan {d['cf'] * 100:.0f}%" for d in rec["diagnosis"]]
    else:
        L.append("  Tidak ditemukan indikasi defisiensi/kelebihan hara; gunakan dosis standar fase.")
    L += ["", "SARAN:"] + [f"  - {s['name']} ({s['cf'] * 100:.0f}%)" for s in rec["saran"]]
    L += ["", "REKOMENDASI DOSIS:"]
    for r in rec["dosis"]["baris"]:
        vals = list(r.values())
        L.append(f"  {vals[0]}: dosis musiman {vals[1]} kg hara/ha; pupuk dasar {vals[2]} kg hara/ha; "
                 f"susulan {vals[3]} kg hara/ha per aplikasi = {vals[5]} kg {vals[4]}/ha ({vals[6]} kg untuk lahan). {vals[7]}")
    L += [f"  * {n}" for n in rec["dosis"]["catatan"]]
    L += ["", "PENJELASAN (HOW):"]
    for lines in rec["how"].values():
        L += lines + [""]
    L += ["ATURAN DIPAKAI: " + ", ".join(rec["aturan_dipakai"]), "", "JEJAK PENALARAN:"]
    L += [f"  {i}. {t}" for i, t in enumerate(rec["trace"], 1)]
    L += ["", "Catatan: hasil hanya alat bantu keputusan; konfirmasi dengan uji tanah atau penyuluh pertanian."]
    return "\n".join(L)


def result_to_csv(rec: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["bagian", "item", "nilai"])
    for d in rec["diagnosis"]:
        w.writerow(["diagnosis", d["name"], f"{d['cf']:.2f}"])
    for s in rec["saran"]:
        w.writerow(["saran", s["name"], f"{s['cf']:.2f}"])
    for r in rec["dosis"]["baris"]:
        vals = list(r.values())
        w.writerow(["dosis", vals[0], f"susulan {vals[3]} kg hara/ha = {vals[5]} kg {vals[4]}/ha; dasar {vals[2]} kg hara/ha"])
    w.writerow(["aturan", "dipakai", " ".join(rec["aturan_dipakai"])])
    return buf.getvalue()


def result_to_pdf(kb, rec: dict) -> bytes:
    """Ekspor laporan ke PDF memakai fpdf2 (font inti, karakter di luar Latin-1 diganti)."""
    from fpdf import FPDF
    text = result_to_text(kb, rec).encode("latin-1", "replace").decode("latin-1")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Laporan Konsultasi Sistem Pakar Pemupukan Cabai", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 8)
    for line in text.split("\n")[2:]:
        pdf.multi_cell(0, 4, line if line else " ", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
