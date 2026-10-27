"""Tab Riwayat konsultasi, filter, statistik penggunaan dan frekuensi aturan."""
import pandas as pd
import streamlit as st

from expert.reporting import compute_stats, filter_history, history_to_csv, load_history


def render(kb, path):
    hist = load_history(path)
    if not hist:
        st.info("Belum ada riwayat konsultasi.")
        return
    st.subheader("Filter riwayat")
    c1, c2, c3, c4 = st.columns(4)
    diag_opts = {"Semua": None, **{v["name"]: k for k, v in kb.conclusions_of_type("diagnosis").items()}}
    dsel = diag_opts[c1.selectbox("Diagnosis", list(diag_opts))]
    fase = c2.selectbox("Fase", ["Semua", "vegetatif", "generatif"])
    min_cf = c3.slider("CF minimum", 0.0, 1.0, 0.0, 0.05)
    dates = c4.date_input("Rentang tanggal", value=[], key="h_dates")
    d_from = dates[0] if len(dates) >= 1 else None
    d_to = dates[1] if len(dates) == 2 else d_from
    sel = filter_history(hist, dsel, min_cf, None if fase == "Semua" else fase, d_from, d_to)
    st.caption(f"{len(sel)} dari {len(hist)} konsultasi")
    table = [{"ID": r["id"], "Waktu": r["waktu"], "Metode": r["mode"], "Fase": r["fase"],
              "Diagnosis utama": r["diagnosis"][0]["name"] if r["diagnosis"] else "-",
              "CF": r["diagnosis"][0]["cf"] if r["diagnosis"] else 0} for r in sel]
    st.dataframe(pd.DataFrame(table), hide_index=True)
    st.download_button("Unduh riwayat (CSV)", history_to_csv(sel), "riwayat_konsultasi.csv", "text/csv")

    st.subheader("Statistik penggunaan")
    s = compute_stats(hist)
    m1, m2 = st.columns(2)
    m1.metric("Total konsultasi", s["total"])
    m2.metric("Rata-rata CF diagnosis utama", f"{s['rata_cf_utama'] * 100:.0f}%")
    if s["diagnosis"]:
        st.markdown("**Frekuensi diagnosis**")
        st.bar_chart(pd.Series(s["diagnosis"]))
    if s["aturan"]:
        st.markdown("**Aturan yang paling sering dipakai**")
        st.bar_chart(pd.Series(s["aturan"]).sort_values(ascending=False))
    st.markdown("**Metode inferensi**")
    st.bar_chart(pd.Series(s["mode"]))
