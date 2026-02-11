# pages/8_Admin_Manualni_Body.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu


def recompute_profiles_points(supabase, user_ids: list[str]):
    """Přepíše profiles.points pro dané uživatele podle:
    predictions.points_awarded + placement_predictions.points_awarded + sum(manual_points_log.change_amount)."""
    if not user_ids:
        return
    match_sum = {uid: 0 for uid in user_ids}
    try:
        preds = supabase.table("predictions").select("user_id, points_awarded").in_("user_id", user_ids).execute().data or []
        for r in preds:
            uid = r.get("user_id")
            if uid in match_sum:
                match_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass
    place_sum = {uid: 0 for uid in user_ids}
    try:
        pp = supabase.table("placement_predictions").select("user_id, points_awarded").in_("user_id", user_ids).execute().data or []
        for r in pp:
            uid = r.get("user_id")
            if uid in place_sum:
                place_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass
    manual_sum = {uid: 0 for uid in user_ids}
    try:
        logs = supabase.table("manual_points_log").select("target_user_id, change_amount").in_("target_user_id", user_ids).execute().data or []
        for r in logs:
            uid = r.get("target_user_id")
            if uid in manual_sum:
                manual_sum[uid] += int(r.get("change_amount") or 0)
    except Exception:
        pass

    for uid in user_ids:
        total = int(match_sum.get(uid, 0)) + int(place_sum.get(uid, 0)) + int(manual_sum.get(uid, 0))
        if total < 0:
            total = 0
        try:
            supabase.table("profiles").update({"points": total}).eq("user_id", uid).execute()
        except Exception:
            pass


load_dotenv()
st.set_page_config(page_title="Admin – Manuální body", page_icon="✏️", layout="wide")

apply_o2_style()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Admin – Manuální body",
    "Přidání / odebrání bodů ručně. Ukládá se do manual_points_log a celkové body se přepočítají.",
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

# load users
users = (supabase.table("profiles").select("user_id, email, points").order("email").execute().data or [])
if not users:
    st.info("Žádní uživatelé v profiles.")
    st.stop()

def user_label(u):
    return f"{u.get('email','—')} • {int(u.get('points') or 0)} bodů"

user_map = {user_label(u): u for u in users}

with card("🎯 Přidat / odebrat body"):
    selected_label = st.selectbox("Uživatel", list(user_map.keys()))
    selected_user = user_map[selected_label]

    current_points = int(selected_user.get("points") or 0)

    points_to_add = st.number_input("Kolik bodů změnit (+ / -)", value=0, step=1)
    reason = st.text_input("Důvod (volitelně)", value="", placeholder="např. doplnění bodů za starý event")

    st.caption(f"Aktuálně: **{current_points}** bodů")

    if st.button("💾 Uložit změnu", type="primary", use_container_width=True):
        try:
            new_points = current_points + int(points_to_add)
            if new_points < 0:
                new_points = 0

            # 1. Vlož záznam do manual_points_log
            log_entry = {
                "admin_user_id": user_id,
                "target_user_id": selected_user["user_id"],
                "change_amount": int(points_to_add),
                "old_points": current_points,
                "new_points": new_points,
                "reason": reason.strip() if reason.strip() else None
            }

            supabase.table("manual_points_log").insert(log_entry).execute()

            # 2. Přepočti profiles.points jednotně (zápasy + umístění + manuální)
            recompute_profiles_points(supabase, [selected_user["user_id"]])

            action = "přidáno" if points_to_add > 0 else "odebráno"
            # načti čerstvé body po přepočtu
            fresh = supabase.table("profiles").select("points").eq("user_id", selected_user["user_id"]).single().execute().data or {}
            fresh_points = int(fresh.get("points") or 0)

            st.success(f"✅ Bodů {action}: {abs(points_to_add)} → {selected_user['email']} má nyní {fresh_points} bodů")

            if reason:
                st.info(f"Důvod: {reason}")

            st.rerun()

        except Exception as e:
            st.error(f"Chyba při ukládání: {e}")
            st.code(str(e))

with card("🧾 Historie manuálních bodů"):
    try:
        logs = (
            supabase.table("manual_points_log")
            .select("created_at, admin_user_id, target_user_id, change_amount, old_points, new_points, reason")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
            .data
            or []
        )
    except Exception:
        logs = []

    if not logs:
        st.info("Zatím žádné manuální zásahy.")
    else:
        # map user_id -> email
        id2email = {u["user_id"]: u.get("email") or u["user_id"] for u in users}

        rows = []
        for r in logs:
            rows.append({
                "Kdy": r.get("created_at"),
                "Komu": id2email.get(r.get("target_user_id"), r.get("target_user_id")),
                "Změna": int(r.get("change_amount") or 0),
                "Poznámka": r.get("reason") or "",
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)