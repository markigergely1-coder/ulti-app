import streamlit as st
from modules.db import get_firestore_db
from modules.pages.game_mode import render_game_mode
from modules.pages.score_entry import render_score_entry
from modules.pages.history import render_history

st.set_page_config(page_title="Ulti App", layout="centered", page_icon="🃏")

st.title("🃏 Ulti App")

fs_db = get_firestore_db()

tab1, tab2, tab3 = st.tabs(["🎮 Játék mód", "📝 Gyors rögzítés", "📊 Előzmények"])

with tab1:
    render_game_mode(fs_db)

with tab2:
    render_score_entry(fs_db)

with tab3:
    render_history(fs_db)
