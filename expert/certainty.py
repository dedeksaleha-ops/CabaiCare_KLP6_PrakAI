"""Modul Certainty Factor (CF) gaya MYCIN.

Semua fungsi murni (tanpa efek samping) sehingga mudah diuji.
"""

# CF input pengguna: seberapa yakin pengguna terhadap gejala yang diamati.
USER_CF_LEVELS = {
    "Tidak yakin": 0.4,
    "Cukup yakin": 0.6,
    "Yakin": 0.8,
    "Sangat yakin": 1.0,
}


def cf_from_mb_md(mb: float, md: float) -> float:
    """CF(H,E) = MB(H,E) - MD(H,E), dengan MB dan MD pada rentang 0..1."""
    if not (0.0 <= mb <= 1.0 and 0.0 <= md <= 1.0):
        raise ValueError("MB dan MD harus berada pada rentang 0..1")
    return round(mb - md, 10)


def cf_conclusion(cf_rule: float, cf_premises: list) -> float:
    """CF kesimpulan satu aturan = CF aturan x min(CF premis) (premis AND)."""
    if not cf_premises:
        return 0.0
    return cf_rule * min(cf_premises)


def cf_combine(a: float, b: float) -> float:
    """Gabungkan dua CF untuk hipotesis yang sama.

    Keduanya positif : a + b(1 - a)   (rumus pada soal)
    Keduanya negatif : a + b(1 + a)
    Beda tanda       : (a + b) / (1 - min(|a|, |b|))
    """
    if a >= 0 and b >= 0:
        return a + b * (1 - a)
    if a <= 0 and b <= 0:
        return a + b * (1 + a)
    denom = 1 - min(abs(a), abs(b))
    return 0.0 if denom == 0 else (a + b) / denom


def cf_combine_many(values: list) -> float:
    """Gabungkan banyak CF secara berurutan."""
    result = 0.0
    for v in values:
        result = cf_combine(result, v)
    return result


def cf_label(cf: float) -> str:
    """Label verbal tingkat kepercayaan."""
    if cf >= 0.9:
        return "sangat tinggi"
    if cf >= 0.7:
        return "tinggi"
    if cf >= 0.5:
        return "sedang"
    if cf >= 0.2:
        return "rendah"
    return "sangat rendah"
