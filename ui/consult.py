"""Tab Konsultasi: input gejala (forward) atau tanya-jawab hipotesis (backward) + tampilan hasil."""
import pandas as pd
import streamlit as st

from expert.certainty import USER_CF_LEVELS, cf_label
from expert.consultation import build_result, set_phase, validate_input
from expert.explanation import explain_why
from expert.inference import InferenceEngine, NeedFact
from expert.reporting import result_to_csv, result_to_pdf, result_to_text, save_consultation
from expert.working_memory import WorkingMemory


def render(kb, history_path):
    mode = st.radio("Metode inferensi", ["Forward Chaining (isi formulir gejala)",
                                         "Backward Chaining (tanya-jawab berbasis hipotesis)"], horizontal=True)
    if mode.startswith("Forward"):
        _forward(kb, history_path)
    else:
        _backward(kb, history_path)
    res = st.session_state.get("result")
    if res and not st.session_state.get("bw"):
        _render_result(kb, res)


def _finish(kb, history_path, wm, mode, fase, luas, trace):
    result = build_result(kb, wm, mode, fase, luas, trace)
    try:
        save_consultation(history_path, result)
    except OSError as exc:
        st.warning(f"Riwayat tidak dapat disimpan: {exc}")
    st.session_state.result = result
    st.session_state.wm_last = wm


def _forward(kb, history_path):
    c1, c2 = st.columns(2)
    fase = c1.radio("Fase pertumbuhan", ["vegetatif", "generatif"], horizontal=True, key="fw_fase",
                    help="Vegetatif: pembentukan akar, batang, daun. Generatif: berbunga dan berbuah.")
    luas = c2.number_input("Luas lahan (m2)", min_value=0.0, value=1000.0, step=100.0, key="fw_luas")
    st.markdown("**Gejala yang teramati** (centang, lalu pilih tingkat keyakinan Anda)")
    groups = {}
    for fid, f in kb.facts.items():
        if f.get("askable", True) and f["category"] != "Konteks":
            groups.setdefault(f["category"], []).append((fid, f))
    selected = {}
    for cat, items in groups.items():
        with st.expander(cat, expanded=True):
            for fid, f in items:
                a, b = st.columns([3, 1.3])
                chk = a.checkbox(f["name"], key=f"fw_chk_{fid}", help="WHY - " + kb.why_text(fid))
                lvl = b.selectbox("Keyakinan", list(USER_CF_LEVELS), index=2, key=f"fw_cf_{fid}",
                                  disabled=not chk, label_visibility="collapsed")
                if chk:
                    selected[fid] = USER_CF_LEVELS[lvl]
    if st.button("Proses diagnosis", type="primary"):
        errors, warnings = validate_input(kb, selected, luas)
        for w in warnings:
            st.warning(w)
        if errors:
            for e in errors:
                st.error(e)
            return
        wm = WorkingMemory()
        for fid, cf in selected.items():
            wm.set_user_fact(fid, cf)
        set_phase(wm, fase)
        trace = InferenceEngine(kb).forward_chain(wm)
        _finish(kb, history_path, wm, "forward", fase, luas, trace)
        st.rerun()


def _backward(kb, history_path):
    bw = st.session_state.get("bw")
    if not bw:
        diag = kb.conclusions_of_type("diagnosis")
        opts = {"Semua hipotesis (diagnosis + saran)": "ALL"}
        opts.update({v["name"]: k for k, v in diag.items()})
        c1, c2, c3 = st.columns(3)
        goal_label = c1.selectbox("Hipotesis yang dibuktikan", list(opts))
        fase = c2.radio("Fase pertumbuhan", ["vegetatif", "generatif"], horizontal=True, key="bw_fase")
        luas = c3.number_input("Luas lahan (m2)", min_value=0.0, value=1000.0, step=100.0, key="bw_luas")
        if st.button("Mulai konsultasi", type="primary"):
            if luas <= 0:
                st.error("Luas lahan harus lebih dari 0 m2.")
                return
            goal = opts[goal_label]
            goals = (list(diag) + list(kb.conclusions_of_type("saran"))) if goal == "ALL" else [goal]
            wm = WorkingMemory()
            set_phase(wm, fase)
            st.session_state.bw = {"goals": goals, "wm": wm, "fase": fase, "luas": luas, "n": 0}
            st.session_state.pop("result", None)
            st.rerun()
        return
    wm, engine = bw["wm"], InferenceEngine(kb)
    try:
        trace = engine.backward_chain(bw["goals"], wm)
    except NeedFact as need:
        st.subheader(f"Pertanyaan {bw['n'] + 1}")
        st.info(kb.name_of(need.fact) + " ?")
        with st.expander("WHY - mengapa sistem menanyakan ini?"):
            st.text(explain_why(kb, need))
        cols = st.columns(5)
        choices = [("Tidak ada", 0.0)] + list(USER_CF_LEVELS.items())
        for col, (label, cf) in zip(cols, choices):
            if col.button(label, key=f"bw_{bw['n']}_{label}"):
                wm.set_user_fact(need.fact, cf)
                bw["n"] += 1
                st.rerun()
        if st.button("Batalkan konsultasi"):
            st.session_state.bw = None
            st.rerun()
        return
    _finish(kb, history_path, wm, "backward", bw["fase"], bw["luas"], trace)
    st.session_state.bw = None
    st.rerun()


def _render_result(kb, res):
    st.divider()
    st.header("Hasil Konsultasi")
    if res["diagnosis"]:
        for d in res["diagnosis"]:
            st.markdown(f"**{d['name']}**")
            st.progress(min(d["cf"], 1.0), text=f"Tingkat kepercayaan {d['cf'] * 100:.0f}% ({cf_label(d['cf'])})")
            info = kb.conclusions[d["id"]]
            st.caption(info["deskripsi"] + "  |  Penanganan: " + info["penanganan"])
    else:
        st.success("Tidak ditemukan indikasi defisiensi atau kelebihan hara. Gunakan dosis standar fase di bawah.")
    if res["saran"]:
        st.subheader("Saran")
        for s in res["saran"]:
            st.markdown(f"- **{s['name']}** ({s['cf'] * 100:.0f}%): {kb.conclusions[s['id']]['penanganan']}")
    with st.expander("Cara membaca hasil"):
        st.markdown(
            "- **CF (Certainty Factor)**: tingkat kepercayaan, 0% sampai 100%.\n"
            "- **Aturan**: pola \"jika gejala ini, maka kesimpulan itu\", masing-masing punya CF aturan.\n"
            "- **min premis**: keyakinan Anda yang paling rendah di antara gejala yang dipakai satu aturan.\n"
            "- **Hitungan satu aturan**: CF aturan x min premis.\n"
            "- **Gabungan**: bila beberapa aturan mendukung kesimpulan yang sama, buktinya digabung dengan "
            "a + b x (1 - a), sehingga naik tetapi tidak pernah melewati 100%.\n"
            "- **Pupuk dasar** diberikan sebelum tanam; **susulan** diberikan bertahap setelah tanam.")
    st.subheader(f"Rekomendasi dosis (fase {res['fase']}, lahan {res['luas_m2']:,.0f} m2)")
    st.dataframe(pd.DataFrame(res["dosis"]["baris"]), hide_index=True)
    for n in res["dosis"]["catatan"]:
        st.caption("* " + n)
    t1, t2, t3, t4 = st.tabs(["HOW - penjelasan", "Aturan dipakai", "Jejak penalaran", "Working memory"])
    with t1:
        for fid, lines in res["how"].items():
            st.text("\n".join(lines))
    with t2:
        for rid in res["aturan_dipakai"]:
            r = kb.rules.get(rid)
            if r:
                st.markdown(f"`{kb.rule_text(r)}`  _[{r.kind}; sumber: {', '.join(r.sources)}]_")
    with t3:
        for i, line in enumerate(res["trace"], 1):
            st.text(f"{i}. {line}")
    with t4:
        st.dataframe(pd.DataFrame(res["memori_log"]), hide_index=True)
    st.subheader("Ekspor laporan")
    a, b, c = st.columns(3)
    a.download_button("Unduh TXT", result_to_text(kb, res), f"konsultasi_{res['id']}.txt", "text/plain")
    b.download_button("Unduh CSV", result_to_csv(res), f"konsultasi_{res['id']}.csv", "text/csv")
    try:
        c.download_button("Unduh PDF", result_to_pdf(kb, res), f"konsultasi_{res['id']}.pdf", "application/pdf")
    except Exception as exc:  # noqa: BLE001 - PDF opsional, jangan mematikan UI
        c.warning(f"PDF gagal dibuat: {exc}")
