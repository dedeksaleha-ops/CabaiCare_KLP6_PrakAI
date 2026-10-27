"""Tab Database hara: deskripsi lengkap dan pencarian gejala."""
import streamlit as st


def render(kb):
    st.subheader("Cari gejala")
    q = st.text_input("Kata kunci gejala (mis. daun, buah, kuning)", key="db_q")
    if q:
        hits = kb.search_facts(q)
        if not hits:
            st.info("Gejala tidak ditemukan.")
        for fid, f in hits:
            used = kb.rules_using(fid)
            targets = sorted({kb.name_of(r.consequent) for r in used})
            st.markdown(f"**{fid}** - {f['name']}  \n_Kategori: {f['category']}. Mengarah ke: {', '.join(targets) or '-'}_")
    st.subheader("Database kondisi hara")
    tipe = st.selectbox("Tampilkan", ["diagnosis", "saran"], key="db_tipe")
    for cid, c in kb.conclusions_of_type(tipe).items():
        with st.expander(f"{c['name']} ({cid})"):
            if c["deskripsi"]:
                st.write(c["deskripsi"])
            if c["penyebab"]:
                st.markdown(f"**Kemungkinan penyebab:** {c['penyebab']}")
            st.markdown(f"**Penanganan:** {c['penanganan']}")
            gejala = sorted({a for r in kb.rules_for(cid) for a in r.antecedents})
            if gejala:
                st.markdown("**Premis terkait:** " + "; ".join(kb.name_of(g) for g in gejala))
            st.caption("Sumber: " + ", ".join(c["sources"]))
