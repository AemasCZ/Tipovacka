# pages/7_Admin_Umisteni.py
import os
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

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
st.set_page_config(page_title="Admin – Umístění", page_icon="🏅", layout="wide")

apply_o2_style()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Admin – Vyhodnocení umístění",
    "Vybereš event, zadáš správné umístění a appka dá 10 bodů za správný tip, 0 za špatný.",
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

events = (supabase.table("placement_events").select("id, title, event_date, correct_value, evaluated_at").order("event_date").execute().data or [])

if not events:
    with card("ℹ️ Info"):
        st.info("V databázi nejsou žádné placement_events.")
    st.stop()

def label_event(e: dict) -> str:
    d = e.get("event_date") or "—"
    cv = e.get("correct_value")
    cv_txt = cv if cv else "—"
    return f"{d} • {e.get('title','—')} • správně: {cv_txt}"

event_map = {label_event(e): e for e in events}

with card("Vyber event", "Vyber disciplínu / umístění."):
    sel = st.selectbox("Event", list(event_map.keys()), label_visibility="collapsed")

event = event_map[sel]
selected_event_id = event["id"]

preds = (supabase.table("placement_predictions").select("user_id, predicted_value, points_awarded").eq("event_id", selected_event_id).execute().data or [])

# map emails
email_map = {}
uids = list({p.get("user_id") for p in preds if p.get("user_id")})
if uids:
    profs = (supabase.table("profiles").select("user_id, email").in_("user_id", uids).execute().data or [])
    email_map = {p["user_id"]: p.get("email") or p["user_id"] for p in profs}

with card("⚙️ Vyhodnocení"):
    current_correct = (event.get("correct_value") or "").strip()
    cv = st.text_input("Správné umístění (přesně jak tipují lidé)", value=current_correct, placeholder="např. 1) USA 2) Kanada 3) Česko")

    colA, colB = st.columns(2)
    with colA:
        do_eval = st.button("✅ Vyhodnotit (10/0)", type="primary", use_container_width=True)
    with colB:
        do_reset = st.button("♻️ Reset", type="secondary", use_container_width=True)

    if do_eval:
        if not cv.strip():
            st.error("Zadej správné umístění.")
        else:
            try:
                cv = cv.strip()
                now_iso = datetime.now(timezone.utc).isoformat()

                supabase.table("placement_events").update({"correct_value": cv, "evaluated_at": now_iso}).eq("id", selected_event_id).execute()

                preds2 = (supabase.table("placement_predictions").select("user_id, predicted_value").eq("event_id", selected_event_id).execute().data or [])
                updated = 0
                affected_uids = []
                for p in preds2:
                    uid = p.get("user_id")
                    if uid:
                        affected_uids.append(uid)
                    pv = (p.get("predicted_value") or "").strip()
                    if not pv:
                        continue
                    pts = 10 if pv == cv else 0
                    supabase.table("placement_predictions").update({"points_awarded": pts, "evaluated_at": now_iso}).eq("event_id", selected_event_id).eq("user_id", p["user_id"]).execute()
                    updated += 1

                # ✅ jednotný přepočet leaderboard bodů
                recompute_profiles_points(supabase, list(sorted(set(affected_uids))))

                st.success(f"Hotovo ✅ Aktualizováno tipů: {updated}")
                st.rerun()

            except Exception as e:
                st.error(f"Vyhodnocení selhalo: {e}")

    if do_reset:
        try:
            supabase.table("placement_events").update({"correct_value": None, "evaluated_at": None}).eq("id", selected_event_id).execute()
            supabase.table("placement_predictions").update({"points_awarded": 0, "evaluated_at": None}).eq("event_id", selected_event_id).execute()
            # ✅ přepočti body dotčeným uživatelům (kteří tipovali tento event)
            affected = [p.get("user_id") for p in preds if p.get("user_id")]
            recompute_profiles_points(supabase, list(sorted(set(affected))))
            st.success("Reset hotov ♻️")
            st.rerun()
        except Exception as e:
            st.error(f"Reset selhal: {e}")

with card("📋 Tipy uživatelů"):
    if not preds:
        st.info("Nikdo zatím netipoval.")
    else:
        rows = []
        for p in preds:
            rows.append({
                "Uživatel": email_map.get(p.get("user_id"), p.get("user_id")),
                "Tip": p.get("predicted_value") or "—",
                "Body": int(p.get("points_awarded") or 0),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)