# pages/3_Leaderboard.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

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
# Supabase
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# session (RLS)
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

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

st.title("🏆 Leaderboard")

# =====================
# admin?
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
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧮 Vyhodnocení zápasů", type="primary"):
            st.switch_page("pages/4_Admin_Vyhodnoceni.py")
    with col2:
        if st.button("🔄 Synchronizace bodů", type="secondary"):
            st.switch_page("pages/5_Admin_Sync_Points.py")
    
    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Leaderboard (body ze součtu predictions.points_awarded)
# =====================
try:
    prof_res = (
        supabase.table("profiles")
        .select("user_id, email")
        .execute()
    )
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profily (RLS?): {e}")
    st.stop()

try:
    preds_res = (
        supabase.table("predictions")
        .select("user_id, points_awarded")
        .execute()
    )
    preds = preds_res.data or []
except Exception as e:
    st.error(f"Nelze načíst tipy (RLS?): {e}")
    st.stop()

# ✅ Spočítáme body pro každého uživatele ze všech predictions
points_by_user = {}
for p in preds:
    uid = p.get("user_id")
    if not uid:
        continue
    awarded = p.get("points_awarded")
    # Ošetříme None hodnoty
    if awarded is None:
        awarded = 0
    points_by_user[uid] = points_by_user.get(uid, 0) + int(awarded)

rows = []
for p in profiles:
    uid = p.get("user_id")
    rows.append(
        {
            "Uživatel": p.get("email") or uid,
            "Body": int(points_by_user.get(uid, 0)),
        }
    )

rows.sort(key=lambda r: r["Body"], reverse=True)

table = []
for i, r in enumerate(rows, start=1):
    table.append(
        {
            "#": i,
            "Uživatel": r["Uživatel"],
            "Body": r["Body"],
        }
    )

if not table:
    st.info("Zatím nejsou žádné tipy s body.")
else:
    st.dataframe(table, use_container_width=True, hide_index=True)

# =====================
# DEBUG sekce (volitelně - můžeš smazat)
# =====================
if is_admin and st.checkbox("🐛 Zobrazit debug info", value=False):
    st.markdown("---")
    st.subheader("Debug: Kontrola synchronizace")
    
    # Načteme profiles.points
    try:
        prof_points = (
            supabase.table("profiles")
            .select("user_id, email, points")
            .execute()
        )
        
        debug_rows = []
        for p in prof_points.data or []:
            uid = p.get("user_id")
            email = p.get("email") or uid
            profile_pts = int(p.get("points") or 0)
            calc_pts = int(points_by_user.get(uid, 0))
            diff = profile_pts - calc_pts
            
            debug_rows.append({
                "Email": email,
                "profiles.points": profile_pts,
                "Σ predictions.points_awarded": calc_pts,
                "Rozdíl": diff
            })
        
        st.dataframe(debug_rows, use_container_width=True, hide_index=True)
        
        if any(r["Rozdíl"] != 0 for r in debug_rows):
            st.warning("⚠️ Nalezeny nesrovnalosti! Možná je potřeba synchronizovat body.")
    except Exception as e:
        st.error(f"Chyba při načítání debug info: {e}")
