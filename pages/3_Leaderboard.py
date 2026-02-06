import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# =====================
# CSS – schová default Streamlit navigaci + header + přidá "robot" vlevo dole
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }

        /* Skrytý admin vstup – robot vlevo dole */
        .admin-fab {
            position: fixed;
            left: 16px;
            bottom: 14px;
            z-index: 9999;
            opacity: 0.18;           /* skoro neviditelné */
            font-size: 22px;
            user-select: none;
            transition: opacity 0.2s ease;
        }
        .admin-fab:hover {
            opacity: 0.75;           /* při najetí myší se ukáže víc */
        }
        .admin-fab a {
            text-decoration: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Leaderboard", page_icon="🏆")

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
# Sidebar – vlastní menu
# =====================
with st.sidebar:
    st.markdown("## 🏒 Tipovačka")
    st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
    st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
    st.markdown("---")

    if st.button("🚪 Odhlásit se"):
        st.session_state.clear()
        st.switch_page("app.py")

# =====================
# Guard: musí být přihlášený
# =====================
user = st.session_state.get("user")
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
# Skrytý admin vstup – když klikneš na robota, přidá se query param ?admin=1
# =====================
st.markdown(
    '<div class="admin-fab"><a href="?admin=1" title="Admin">🤖</a></div>',
    unsafe_allow_html=True
)

# Pokud je v URL admin=1, ověř admina a přesměruj
qp = st.query_params
if str(qp.get("admin", "")) == "1":
    try:
        prof = (
            supabase.table("profiles")
            .select("is_admin")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        is_admin = bool((prof.data or {}).get("is_admin", False))
    except Exception:
        is_admin = False

    if is_admin:
        # vyčisti query param, ať se to netočí při refreshi
        st.query_params.clear()
        st.switch_page("pages/1_Soupisky_Admin.py")
        st.stop()
    else:
        st.query_params.clear()
        st.warning("Admin přístup nemáš.")
        st.stop()

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