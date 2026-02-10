# pages/3_Leaderboard.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Leaderboard", page_icon="🏆", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

apply_o2_style()

user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Leaderboard",
    "Celkové pořadí tipující. Body = součet bodů za zápasy + umístění + manuální body.",
    image_path="assets/olympic.jpeg",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
        st.stop()

# --- načti profily ---
try:
    prof_res = supabase.table("profiles").select("user_id, email, is_admin, points").execute()
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profiles: {e}")
    st.stop()

if not profiles:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádní uživatelé v profiles.")
        st.stop()

# Seřazení podle bodů (nejvíce bodů nahoře)
profiles.sort(key=lambda x: (-int(x.get("points", 0) or 0), x.get("email", "")))

# Admin box
is_admin = any(p["user_id"] == user_id and p.get("is_admin") for p in profiles)
if is_admin:
    with card("🛠️ Admin", "Rychlé odkazy"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("🧮 Vyhodnocení zápasů", type="primary", use_container_width=True):
                st.switch_page("pages/4_Admin_Vyhodnoceni.py")
        with c2:
            if st.button("🏅 Vyhodnocení umístění", type="primary", use_container_width=True):
                st.switch_page("pages/7_Admin_Umisteni.py")
        with c3:
            if st.button("✏️ Manuální body", type="secondary", use_container_width=True):
                st.switch_page("pages/8_Admin_Manualni_Body.py")
        with c4:
            if st.button("🔄 Sync body", type="secondary", use_container_width=True):
                st.switch_page("pages/5_Admin_Sync_Points.py")

# Hlavní tabulka leaderboardu
with card("🏆 Pořadí"):
    if not profiles:
        st.info("Zatím nejsou žádní uživatelé.")
    else:
        # Vytvoření tabulky pro zobrazení
        table_rows = []
        for i, p in enumerate(profiles, start=1):
            # Email s medailemi pro první 3 místa
            email = p.get("email", "—")
            if i == 1:
                email = f"🥇 {email}"
            elif i == 2:
                email = f"🥈 {email}"
            elif i == 3:
                email = f"🥉 {email}"
            
            table_rows.append({
                "#": i,
                "Uživatel": email,
                "Body": int(p.get("points", 0) or 0)
            })
        
        # Zobraz tabulku
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

# Debug info pro admina (volitelné)
if is_admin:
    with st.expander("🔍 Debug info (jen pro adminy)"):
        st.markdown("**Raw data z databáze:**")
        debug_data = []
        for p in profiles:
            debug_data.append({
                "user_id": p.get("user_id", "—"),
                "email": p.get("email", "—"),
                "points": p.get("points", 0),
                "is_admin": p.get("is_admin", False)
            })
        st.dataframe(debug_data, use_container_width=True, hide_index=True)