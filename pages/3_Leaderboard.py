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
        .title { font-size: 34px; font-weight: 900; margin: 0 0 6px 0; }
        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
    </style>
    """,
    unsafe_allow_html=True,
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

# Session (pro RLS)
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
    st.warning("Nejsi přihlášený. Jdi do Login.")
    st.stop()

st.title("🏆 Leaderboard")
st.caption("Body se počítají živě z tipů (umístění + případně zápasy).")

# =====================
# Načíst profily
# =====================
try:
    prof_res = (
        supabase.table("profiles")
        .select("user_id, email, is_admin")
        .execute()
    )
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profiles: {e}")
    st.stop()

if not profiles:
    st.info("Zatím nejsou žádní uživatelé v profiles.")
    st.stop()

# map: user_id -> email
email_by_uid = {p["user_id"]: (p.get("email") or "—") for p in profiles}

# =====================
# Sečíst body z UMÍSTĚNÍ
# =====================
placement_points = {uid: 0 for uid in email_by_uid.keys()}
try:
    pp_res = (
        supabase.table("placement_predictions")
        .select("user_id, points_awarded")
        .execute()
    )
    pp = pp_res.data or []
    for row in pp:
        uid = row.get("user_id")
        pts = int(row.get("points_awarded") or 0)
        if uid in placement_points:
            placement_points[uid] += pts
except Exception:
    # když tabulka neexistuje / RLS / cokoliv – leaderboard pořád poběží
    pass

# =====================
# Sečíst body ze ZÁPASŮ (pokud existuje match_predictions)
# =====================
match_points = {uid: 0 for uid in email_by_uid.keys()}
try:
    mp_res = (
        supabase.table("match_predictions")
        .select("user_id, points_awarded")
        .execute()
    )
    mp = mp_res.data or []
    for row in mp:
        uid = row.get("user_id")
        pts = int(row.get("points_awarded") or 0)
        if uid in match_points:
            match_points[uid] += pts
except Exception:
    pass

# =====================
# Složit leaderboard
# =====================
rows = []
for p in profiles:
    uid = p["user_id"]
    rows.append(
        {
            "Uživatel": email_by_uid.get(uid, "—"),
            "Umístění": placement_points.get(uid, 0),
            "Zápasy": match_points.get(uid, 0),
            "Body": placement_points.get(uid, 0) + match_points.get(uid, 0),
            "_is_admin": bool(p.get("is_admin")),
        }
    )

rows.sort(key=lambda x: (-x["Body"], x["Uživatel"]))

# =====================
# Admin box (tlačítka)
# =====================
is_admin = any(p["user_id"] == user_id and p.get("is_admin") for p in profiles)
if is_admin:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛠️ Admin")
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1:
        if st.button("🧮 Vyhodnocení zápasů", use_container_width=True):
            st.switch_page("pages/5_Admin_Zapasy.py")  # uprav název souboru podle sebe
    with c2:
        if st.button("🧮 Vyhodnocení umístění", use_container_width=True):
            st.switch_page("pages/7_Admin_Umisteni.py")
    with c3:
        st.button("🔄 Synchronizace bodů", use_container_width=True, disabled=True)
    st.caption("Pozn.: Body se teď počítají živě, synchronizace není potřeba.")
    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Tabulka
# =====================
# pořadí + TOP štítek
table_rows = []
for i, r in enumerate(rows, start=1):
    user_label = r["Uživatel"]
    if i == 1:
        user_label = f"{user_label}   🥇 TOP"
    table_rows.append(
        {
            "#": i,
            "Uživatel": user_label,
            "Body": r["Body"],
        }
    )

st.dataframe(table_rows, use_container_width=True, hide_index=True)