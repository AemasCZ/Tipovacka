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
    "Součet bodů ze zápasů + umístění. Počítáno živě z databáze.",
    image_path="assets/olymp.png",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

# --- profily ---
try:
    prof_res = supabase.table("profiles").select("user_id, email, is_admin").execute()
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profiles: {e}")
    st.stop()

if not profiles:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádní uživatelé v profiles.")
    st.stop()

email_by_uid = {p["user_id"]: (p.get("email") or "—") for p in profiles}
uids = list(email_by_uid.keys())

# --- zápasy body ---
match_points = {uid: 0 for uid in uids}
try:
    res = supabase.table("predictions").select("user_id, points_awarded").execute()
    rows = res.data or []
    for r in rows:
        uid = r.get("user_id")
        if uid in match_points:
            match_points[uid] += int(r.get("points_awarded") or 0)
except Exception:
    pass

# --- umístění body ---
placement_points = {uid: 0 for uid in uids}
try:
    res = supabase.table("placement_predictions").select("user_id, points_awarded").execute()
    rows = res.data or []
    for r in rows:
        uid = r.get("user_id")
        if uid in placement_points:
            placement_points[uid] += int(r.get("points_awarded") or 0)
except Exception:
    pass

rows = []
for p in profiles:
    uid = p["user_id"]
    rows.append({
        "Uživatel": email_by_uid.get(uid, "—"),
        "Zápasy": match_points.get(uid, 0),
        "Umístění": placement_points.get(uid, 0),
        "Body": match_points.get(uid, 0) + placement_points.get(uid, 0),
        "_is_admin": bool(p.get("is_admin")),
    })

rows.sort(key=lambda x: (-x["Body"], x["Uživatel"]))

# Admin box
is_admin = any(p["user_id"] == user_id and p.get("is_admin") for p in profiles)
if is_admin:
    with card("🛠️ Admin", "Rychlé odkazy"):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🧮 Vyhodnocení zápasů", type="primary", use_container_width=True):
                st.switch_page("pages/4_Admin_Vyhodnoceni.py")
        with c2:
            if st.button("🏅 Vyhodnocení umístění", type="primary", use_container_width=True):
                st.switch_page("pages/7_Admin_Umisteni.py")
        with c3:
            if st.button("🔄 Sync body (profiles.points)", type="secondary", use_container_width=True):
                st.switch_page("pages/5_Admin_Sync_Points.py")

# Tabulka
table_rows = []
for i, r in enumerate(rows, start=1):
    label = r["Uživatel"]
    if i == 1:
        label = f"{label} 🥇"
    table_rows.append({"#": i, "Uživatel": label, "Zápasy": r["Zápasy"], "Umístění": r["Umístění"], "Body": r["Body"]})

with card("🏆 Pořadí"):
    st.dataframe(table_rows, use_container_width=True, hide_index=True)