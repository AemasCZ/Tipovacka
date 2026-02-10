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
    prof_res = supabase.table("profiles").select("user_id, email, is_admin").execute()
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profiles: {e}")
    st.stop()

if not profiles:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádní uživatelé v profiles.")
        st.stop()

# Vytvoř mapu emailů
email_by_uid = {p["user_id"]: (p.get("email") or "—") for p in profiles}
uids = list(email_by_uid.keys())

# --- ZÁPASY BODY ---
match_points = {uid: 0 for uid in uids}
try:
    res = supabase.table("predictions").select("user_id, points_awarded").execute()
    rows_pred = res.data or []
    for r in rows_pred:
        uid = r.get("user_id")
        if uid in match_points:
            match_points[uid] += int(r.get("points_awarded") or 0)
except Exception as e:
    st.error(f"Chyba při načítání bodů ze zápasů: {e}")

# --- UMÍSTĚNÍ BODY ---
placement_points = {uid: 0 for uid in uids}
try:
    res = supabase.table("placement_predictions").select("user_id, points_awarded").execute()
    rows_place = res.data or []
    for r in rows_place:
        uid = r.get("user_id")
        if uid in placement_points:
            placement_points[uid] += int(r.get("points_awarded") or 0)
except Exception as e:
    st.error(f"Chyba při načítání bodů z umístění: {e}")

# --- MANUÁLNÍ BODY ---
manual_points = {uid: 0 for uid in uids}
try:
    res = supabase.table("manual_points_log").select("target_user_id, change_amount").execute()
    rows_manual = res.data or []
    for r in rows_manual:
        uid = r.get("target_user_id")
        if uid in manual_points:
            manual_points[uid] += int(r.get("change_amount") or 0)
except Exception as e:
    st.error(f"Chyba při načítání manuálních bodů: {e}")

# --- SESTAVENÍ ŘÁDKŮ S CELKOVÝMI BODY ---
rows = []
for p in profiles:
    uid = p["user_id"]
    email = email_by_uid.get(uid, "—")
    
    # Sečti všechny body ze zdrojů
    total_points = (
        match_points.get(uid, 0) + 
        placement_points.get(uid, 0) + 
        manual_points.get(uid, 0)
    )
    
    rows.append({
        "user_id": uid,
        "email": email,
        "total_points": total_points,
        "is_admin": bool(p.get("is_admin"))
    })

# Seřazení podle bodů (nejvíce bodů nahoře)
rows.sort(key=lambda x: (-x["total_points"], x["email"]))

# Admin box (jen pro adminy)
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

# --- HLAVNÍ TABULKA (STEJNÁ PRO VŠECHNY) ---
with card("🏆 Pořadí"):
    if not rows:
        st.info("Zatím nejsou žádní uživatelé.")
    else:
        # Vytvoření tabulky pro zobrazení
        table_rows = []
        for i, r in enumerate(rows, start=1):
            # Email s medailemi pro první 3 místa
            email_display = r["email"]
            if i == 1:
                email_display = f"🥇 {email_display}"
            elif i == 2:
                email_display = f"🥈 {email_display}"
            elif i == 3:
                email_display = f"🥉 {email_display}"
            
            table_rows.append({
                "#": i,
                "Uživatel": email_display,
                "Body": r["total_points"]
            })
        
        # Zobraz tabulku
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

# Debug info pro admina
if is_admin:
    with st.expander("🔍 Debug info (jen pro adminy)"):
        st.markdown("**Rozklad bodů podle zdrojů:**")
        
        debug_rows = []
        for r in rows:
            uid = r["user_id"]
            debug_rows.append({
                "Email": r["email"],
                "Zápasy": match_points.get(uid, 0),
                "Umístění": placement_points.get(uid, 0),
                "Manuální": manual_points.get(uid, 0),
                "Celkem": r["total_points"]
            })
        
        st.dataframe(debug_rows, use_container_width=True, hide_index=True)
        
        st.caption("💡 Tato tabulka ukazuje rozklad bodů ze všech zdrojů v databázi.")