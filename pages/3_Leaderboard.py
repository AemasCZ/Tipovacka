# pages/3_Leaderboard.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Leaderboard", page_icon="🏆", layout="wide")

# =====================
# CSS
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }

        .block-container { padding-top: 1.2rem; }

        .card {
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            border-radius: 16px;
            padding: 16px;
            margin: 10px 0 16px 0;
        }
        .muted { opacity: 0.75; font-size: 14px; }
        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
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

# ✅ session (RLS)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# =====================
# Guard: login
# =====================
user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# =====================
# UI
# =====================
st.title("🏆 Leaderboard")

# =====================
# Admin?
# =====================
is_admin = False
try:
    my_prof = (
        supabase.table("profiles")
        .select("is_admin")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    is_admin = bool((my_prof.data or {}).get("is_admin", False))
except Exception:
    is_admin = False

if is_admin:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛠️ Admin")
    st.markdown('<div class="muted">Vyhodnocení zápasů a přepočet bodů.</div>', unsafe_allow_html=True)
    if st.button("🧮 Vyhodnocení zápasů", type="primary"):
        st.switch_page("pages/4_Admin_Vyhodnoceni.py")
    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Load leaderboard
# =====================
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
    st.stop()

# =====================
# Render table
# =====================
table = []
for i, r in enumerate(rows, start=1):
    table.append(
        {
            "#": i,
            "Uživatel": r.get("email") or "—",
            "Body": int(r.get("points") or 0),
        }
    )

st.dataframe(table, use_container_width=True, hide_index=True)