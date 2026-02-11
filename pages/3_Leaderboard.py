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

# Session pro RLS (stejný pattern jako jinde)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

apply_o2_style()

user = st.session_state.get("user")
user_id = user["id"] if user else None

render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Leaderboard",
    "Celkové pořadí tipujících. Body = součet (zápasy + umístění + manuální).",
    image_path="assets/olympic.jpeg",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

# --- Načti profily (toto musí být povolené pro všechny) ---
try:
    prof_res = supabase.table("profiles").select("user_id, email, points, is_admin").execute()
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profiles: {e}")
    st.stop()

if not profiles:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádní uživatelé v profiles.")
    st.stop()

# zjisti, zda jsem admin
me = next((p for p in profiles if p.get("user_id") == user_id), None)
is_admin = bool((me or {}).get("is_admin", False))

# ---------- PRO VŠECHNY: leaderboard podle profiles.points ----------
rows = []
for p in profiles:
    uid = p.get("user_id")
    if not uid:
        continue
    rows.append({
        "user_id": uid,
        "email": p.get("email") or "—",
        "total": int(p.get("points") or 0),  # ✅ SOUČET = profiles.points
    })

rows.sort(key=lambda x: (-x["total"], x["email"]))

# ---------- ADMIN: dopočítej rozpad (zápasy/umístění/manuální) ----------
match_sum = {}
place_sum = {}
manual_sum = {}

if is_admin:
    user_ids = [r["user_id"] for r in rows]

    match_sum = {uid: 0 for uid in user_ids}
    place_sum = {uid: 0 for uid in user_ids}
    manual_sum = {uid: 0 for uid in user_ids}

    try:
        preds = (
            supabase.table("predictions")
            .select("user_id, points_awarded")
            .in_("user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in preds:
            uid = r.get("user_id")
            if uid in match_sum:
                match_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass

    try:
        pp = (
            supabase.table("placement_predictions")
            .select("user_id, points_awarded")
            .in_("user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in pp:
            uid = r.get("user_id")
            if uid in place_sum:
                place_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass

    try:
        logs = (
            supabase.table("manual_points_log")
            .select("target_user_id, change_amount")
            .in_("target_user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in logs:
            uid = r.get("target_user_id")
            if uid in manual_sum:
                manual_sum[uid] += int(r.get("change_amount") or 0)
    except Exception:
        pass


# --- ADMIN box (jen pro adminy) ---
if is_admin:
    with card("🛠️ Admin", "Rychlé odkazy"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("🧮 Vyhodnocení zápasů", type="primary", use_container_width=True, key="lb_admin_matches"):
                st.switch_page("pages/4_Admin_Vyhodnoceni.py")
        with c2:
            if st.button("🏅 Vyhodnocení umístění", type="primary", use_container_width=True, key="lb_admin_place"):
                st.switch_page("pages/7_Admin_Umisteni.py")
        with c3:
            if st.button("✏️ Manuální body", type="secondary", use_container_width=True, key="lb_admin_manual"):
                st.switch_page("pages/8_Admin_Manualni_Body.py")
        with c4:
            if st.button("🔄 Sync body", type="secondary", use_container_width=True, key="lb_admin_sync"):
                st.switch_page("pages/5_Admin_Sync_Points.py")


# --- HLAVNÍ TABULKA ---
with card("🏆 Pořadí"):
    table_rows = []
    for i, r in enumerate(rows, start=1):
        email_display = r["email"]
        if i == 1:
            email_display = f"🥇 {email_display}"
        elif i == 2:
            email_display = f"🥈 {email_display}"
        elif i == 3:
            email_display = f"🥉 {email_display}"

        # ✅ PRO VŠECHNY (admin i neadmin) = profiles.points
        base = {
            "#": i,
            "Uživatel": email_display,
            "Body celkem": r["total"],  # ✅ profiles.points = zápasy + umístění + manuální
        }

        # ✅ ADMIN vidí navíc rozpad pro kontrolu
        if is_admin:
            uid = r["user_id"]
            base["└─ Zápasy"] = int(match_sum.get(uid, 0))
            base["└─ Umístění"] = int(place_sum.get(uid, 0))
            base["└─ Manuální"] = int(manual_sum.get(uid, 0))

        table_rows.append(base)

    st.dataframe(table_rows, use_container_width=True, hide_index=True)

# --- Debug jen pro admina ---
if is_admin:
    with st.expander("🔍 Debug (kontrola součtu)"):
        st.caption("Porovnání: profiles.points vs. (zápasy+umístění+manuální).")
        dbg = []
        for r in rows:
            uid = r["user_id"]
            parts = int(match_sum.get(uid, 0)) + int(place_sum.get(uid, 0)) + int(manual_sum.get(uid, 0))
            dbg.append({
                "email": r["email"],
                "profiles.points": r["total"],
                "parts_sum": parts,
                "zápasy": int(match_sum.get(uid, 0)),
                "umístění": int(place_sum.get(uid, 0)),
                "manuální": int(manual_sum.get(uid, 0)),
            })
        st.dataframe(dbg, use_container_width=True, hide_index=True)