"""Explanation Facility: WHY (mengapa bertanya) dan HOW (bagaimana kesimpulan diperoleh)."""
from .certainty import cf_combine, cf_label


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def explain_why(kb, need) -> str:
    """Jelaskan mengapa sistem menanyakan fakta tertentu pada backward chaining."""
    lines = [f"Sistem bertanya: \"{kb.name_of(need.fact)}\"."]
    if need.rule_id:
        rule = kb.rules[need.rule_id]
        lines.append(f"Alasan: ini salah satu syarat pada aturan {rule.id}. {kb.rule_sentence(rule)}.")
    if need.stack:
        top = need.stack[0][0]
        lines.append(f"Yang sedang dibuktikan: {kb.name_of(top)}.")
        chain = " > ".join(kb.name_of(g) + f" (aturan {r})" for g, r in need.stack)
        lines.append(f"Urutan penalaran: {chain}.")
    return "\n".join(lines)


def explain_how(kb, wm, fid: str, indent: int = 0, _seen=None) -> list:
    """Susun penjelasan HOW (bahasa sehari-hari) sebagai daftar baris.

    Menjelaskan tiap aturan yang mendukung kesimpulan, cara menghitung keyakinannya,
    dan cara beberapa bukti digabung. Kesimpulan antara dijelaskan di bawahnya (menjorok).
    """
    _seen = _seen if _seen is not None else set()
    pad = "      " * indent
    name = kb.name_of(fid)
    if fid in wm.user_facts:
        return [f"{pad}- {name} (keyakinan Anda {_pct(wm.user_facts[fid])})"]
    if fid not in wm.derivations:
        return [f"{pad}- {name} (tidak terbukti)"]
    cf = wm.inferred[fid]
    head = "Kesimpulan" if indent == 0 else "Kesimpulan antara"
    lines = [f"{pad}{head}: {name}, kepercayaan {_pct(cf)} ({cf_label(cf)})"]
    if fid in _seen:
        return lines + [f"{pad}  (penjelasan lengkap ada di atas)"]
    _seen.add(fid)
    if indent == 0:
        lines.append(f"{pad}Cara sistem sampai ke kesimpulan ini:")
    derivs = wm.derivations[fid]
    for i, d in enumerate(derivs, 1):
        rule = kb.rules.get(d["rule"])
        lines.append(f"{pad}  Bukti {i} (aturan {d['rule']}):")
        if rule:
            lines.append(f"{pad}    Artinya: {kb.rule_sentence(rule)}")
        lines.append(f"{pad}    Syarat yang terpenuhi:")
        for p, pcf in d["premises"].items():
            kind = "keyakinan Anda" if p in wm.user_facts else "hasil penalaran"
            lines.append(f"{pad}      - {kb.name_of(p)} ({kind} {_pct(pcf)})")
        lines.append(f"{pad}    Perhitungan: CF aturan {_pct(d['cf_rule'])} x min premis {_pct(d['cf_min'])} "
                     f"= {_pct(d['contrib'])}")
        for p in d["premises"]:
            if p not in wm.user_facts:
                lines.extend(explain_how(kb, wm, p, indent + 1, _seen))
    if len(derivs) > 1:
        running = derivs[0]["contrib"]
        lines.append(f"{pad}  Penggabungan bukti (CF gabungan = a + b x (1 - a)):")
        for i, d in enumerate(derivs[1:], 2):
            new = cf_combine(running, d["contrib"])
            left = f"Bukti 1 ({_pct(running)})" if i == 2 else f"Hasil gabungan sebelumnya ({_pct(running)})"
            lines.append(f"{pad}    {left} + bukti {i} ({_pct(d['contrib'])}) = {_pct(new)}")
            running = new
    return lines
