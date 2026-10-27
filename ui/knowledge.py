"""Tab Basis Pengetahuan: lihat, cari, tambah, ubah, hapus aturan (Knowledge Acquisition)."""
import pandas as pd
import streamlit as st

from expert.knowledge_base import KnowledgeBaseError
from expert.models import Rule


def render(kb):
    st.subheader("Daftar aturan")
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Cari aturan (id, gejala, kesimpulan)", key="kb_q")
    kind = c2.selectbox("Jenis", ["semua", "faktual", "heuristik"], key="kb_kind")
    goal = c3.selectbox("Kesimpulan", ["semua"] + list(kb.conclusions), key="kb_goal")
    rows = []
    for r in kb.rules.values():
        text = (kb.rule_text(r, with_names=True)).lower()
        if q and q.lower() not in text:
            continue
        if kind != "semua" and r.kind != kind:
            continue
        if goal != "semua" and r.consequent != goal:
            continue
        rows.append({"ID": r.id, "IF": " AND ".join(r.antecedents), "THEN": r.consequent, "CF": r.cf,
                     "Jenis": r.kind, "Sumber": ", ".join(r.sources), "Catatan": r.note})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption(f"{len(rows)} dari {len(kb.rules)} aturan. 'Heuristik' = pertimbangan perancang yang perlu divalidasi pakar.")

    st.subheader("Akuisisi pengetahuan")
    action = st.radio("Aksi", ["Tambah", "Ubah", "Hapus"], horizontal=True, key="kb_action")
    options = list(kb.facts) + list(kb.conclusions)
    fmt = lambda x: f"{x} - {kb.name_of(x)}"
    if action == "Tambah":
        nums = [int(r.id[1:]) for r in kb.rules.values() if r.id[1:].isdigit()]
        default = Rule(id=f"R{max(nums, default=0) + 1:02d}", antecedents=[], consequent=list(kb.conclusions)[0], cf=0.5)
        _form(kb, default, is_new=True)
    else:
        rid = st.selectbox("Pilih aturan", list(kb.rules), key="kb_pick")
        if not rid:
            return
        if action == "Ubah":
            _form(kb, kb.rules[rid], is_new=False)
        else:
            st.code(kb.rule_text(kb.rules[rid], with_names=True))
            if st.checkbox("Saya yakin ingin menghapus aturan ini", key="kb_del_ok"):
                if st.button("Hapus aturan", type="primary"):
                    try:
                        warnings = kb.delete_rule(rid)
                    except KnowledgeBaseError as exc:
                        st.error(str(exc))
                        return
                    st.success(f"Aturan {rid} dihapus.")
                    for w in warnings:
                        st.warning(w)
    with st.expander("Pulihkan knowledge base awal"):
        if st.button("Pulihkan ke versi awal"):
            try:
                kb.restore_default()
                st.success("Knowledge base dipulihkan.")
            except KnowledgeBaseError as exc:
                st.error(str(exc))


def _form(kb, rule, is_new):
    options = list(kb.facts) + list(kb.conclusions)
    fmt = lambda x: f"{x} - {kb.name_of(x)}"
    k = f"kbf_{'new' if is_new else rule.id}"
    with st.form(k):
        rid = st.text_input("ID aturan", value=rule.id, disabled=not is_new)
        ante = st.multiselect("IF (antecedent, digabung AND)", options, default=rule.antecedents, format_func=fmt)
        goals = list(kb.conclusions)
        cons = st.selectbox("THEN (consequent)", goals, index=goals.index(rule.consequent) if rule.consequent in goals else 0, format_func=fmt)
        cf = st.number_input("CF aturan (-1.0 s.d. 1.0)", min_value=-1.0, max_value=1.0, value=float(rule.cf), step=0.05)
        kind = st.selectbox("Jenis pengetahuan", ["faktual", "heuristik"], index=0 if rule.kind == "faktual" else 1)
        src = st.multiselect("Sumber (wajib)", list(kb.sources), default=rule.sources)
        note = st.text_input("Catatan", value=rule.note)
        if st.form_submit_button("Simpan aturan"):
            new = Rule(id=rid.strip(), antecedents=ante, consequent=cons, cf=round(cf, 2), kind=kind, sources=src, note=note)
            try:
                errors = kb.add_rule(new) if is_new else kb.update_rule(new)
            except KnowledgeBaseError as exc:
                st.error(str(exc))
                return
            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.success(f"Aturan {new.id} disimpan.")
