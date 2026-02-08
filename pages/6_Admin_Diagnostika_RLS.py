# pages/6_Admin_Diagnostika_RLS.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Admin – Diagnostika RLS", page_icon="🔍", layout="wide")

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
    "Admin – Diagnostika RLS",
    "Ukáže, co aktuálně přihlášený uživatel vidí přes RLS policies.",
    image_path="assets/olymp.png",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

# admin check
try:
    prof = supabase.table("profiles").select("user_id, is_admin").eq("user_id", user["id"]).single().execute()
    if not (prof.data or {}).get("is_admin"):
        st.error("Tato stránka je jen pro admina.")
        st.stop()
except Exception as e:
    st.error(f"Nelze ověřit admina: {e}")
    st.stop()

with card("1️⃣ profiles"):
    try:
        profiles = supabase.table("profiles").select("user_id, email, points, is_admin").execute().data or []
        st.success(f"✅ Vidím {len(profiles)} profilů")
        st.dataframe(profiles, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ profiles read: {e}")
        st.code(str(e))

with card("2️⃣ predictions"):
    try:
        preds = supabase.table("predictions").select("user_id, match_id, home_score, away_score, points_awarded, scorer_name").execute().data or []
        st.success(f"✅ Vidím {len(preds)} tipů")
        st.dataframe(preds, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ predictions read: {e}")
        st.code(str(e))
        st.warning("Pokud nevidíš tipy všech uživatelů, leaderboard nebude umět sečíst body.")

with card("3️⃣ matches"):
    try:
        matches = supabase.table("matches").select("id, home_team, away_team, starts_at, final_home_score, final_away_score").execute().data or []
        st.success(f"✅ Vidím {len(matches)} zápasů")
        st.dataframe(matches, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ matches read: {e}")
        st.code(str(e))

with card("4️⃣ scorer_results"):
    try:
        rows = supabase.table("scorer_results").select("match_id, scorer_name, scorer_team, did_score").execute().data or []
        st.success(f"✅ Vidím {len(rows)} záznamů")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"❌ scorer_results read: {e}")
        st.code(str(e))