"""Aplikasi Streamlit: Sistem Pakar Rekomendasi Pemupukan Cabai (rule-based)."""
import os

import streamlit as st

from expert.knowledge_base import KnowledgeBase, KnowledgeBaseError
from ui import about, consult, database, history, knowledge

BASE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE, "data", "knowledge_base.json")
HISTORY_PATH = os.path.join(BASE, "data", "history.json")

st.set_page_config(page_title="Sistem Pakar Pemupukan Cabai", layout="wide")


def get_kb() -> KnowledgeBase:
    """Ambil knowledge base dari session; muat ulang bila file berubah."""
    if "kb" not in st.session_state:
        st.session_state.kb = KnowledgeBase(KB_PATH)
    kb = st.session_state.kb
    kb.reload_if_changed()
    return kb


def main():
    st.title("Sistem Pakar Rekomendasi Pemupukan Cabai")
    st.caption("Kecerdasan Artifisial - Rule-Based System | Forward & Backward Chaining + Certainty Factor")
    try:
        kb = get_kb()
    except KnowledgeBaseError as exc:
        st.error(str(exc))
        st.stop()
    tabs = st.tabs(["Konsultasi", "Basis Pengetahuan", "Database Hara & Pencarian", "Riwayat & Statistik", "Tentang & Referensi"])
    with tabs[0]:
        consult.render(kb, HISTORY_PATH)
    with tabs[1]:
        knowledge.render(kb)
    with tabs[2]:
        database.render(kb)
    with tabs[3]:
        history.render(kb, HISTORY_PATH)
    with tabs[4]:
        about.render(kb)


main()
