import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky (MUSÍ BÝT PRVNÍ Streamlit příkaz)
# =====================
load_dotenv()
st.set_page_config(page_title="Leaderboard", page_icon="🏆")

# =====================
# CSS – schová default Streamlit navigaci + header
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# Supabase klient
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ✅ Navázání session (nutné pro RLS)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# =====================
# Guard: musí být přihlášený
# =====================
user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

# Pokud máš RLS, bez tokenů to může padat
if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

user_id = user["id"]

# =====================
# UI
# =====================
st.title("🏆 Leaderboard")

try:
    res = (
        supabase.table("profiles")
        .select("email, points")
        .order("points", desc=True)
        .execute()
    )
    rows = res.data or []
except Exception as e:
    st.error(f"Nelze načíst leaderboard: {e}")
    st.stop()

if not rows:
    st.info("Zatím žádná data.")
else:
    table = []
    for i, r in enumerate(rows, start=1):
        table.append({"#": i, "Uživatel": r["email"], "Body": r["points"]})

    st.dataframe(table, use_container_width=True, hide_index=True)
