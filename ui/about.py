"""Tab Tentang sistem dan daftar referensi (beserta status verifikasi)."""
import streamlit as st


def render(kb):
    st.subheader("Tentang sistem")
    st.write("Sistem pakar rule-based untuk menentukan jenis dan dosis pupuk cabai berdasarkan fase "
             "pertumbuhan (vegetatif/generatif) dan gejala visual defisiensi atau kelebihan hara. "
             "Hasil adalah alat bantu keputusan; dosis akhir sebaiknya dikonfirmasi dengan uji tanah dan penyuluh pertanian.")
    st.warning("Hubungan gejala-hara pada aturan 'faktual' didukung sumber yang sudah dibaca. Nilai CF aturan, aturan "
               "'heuristik', dan faktor penyesuaian dosis adalah estimasi perancang yang perlu divalidasi pakar. "
               "Gejala pada layar tidak selalu jelas dan bisa tertutup faktor lain (S2); uji tanah lebih pasti.")
    st.subheader("Referensi")
    for sid, s in kb.sources.items():
        st.markdown(f"**{sid}.** {s['ref']}")
        if s["url"]:
            st.markdown(f"[{s['url']}]({s['url']})")
        st.markdown("**Dipakai untuk:** " + s["didukung"])
        st.markdown("**Batasan:** " + s["batasan"])
