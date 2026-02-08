# pages/5_Admin_Sync_Points.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Admin – Sync bodů", page_icon="🔄", layout="wide")

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
    "Admin – Synchronizace bodů",
    "Přepíše profiles.points podle součtu predictions.points_awarded + placement_predictions.points_awarded.",
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

# load profiles
profiles = (supabase.table("profiles").select("user_id, email, points").execute().data or [])

# sums from predictions
match_sum = {}
try:
    preds = (supabase.table("predictions").select("user_id, points_awarded").execute().data or [])
    for p in preds:
        uid = p.get("user_id")
        match_sum[uid] = match_sum.get(uid, 0) + int(p.get("points_awarded") or 0)
except Exception:
    pass

# sums from placement_predictions
place_sum = {}
try:
    pp = (supabase.table("placement_predictions").select("user_id, points_awarded").execute().data or [])
    for p in pp:
        uid = p.get("user_id")
        place_sum[uid] = place_sum.get(uid, 0) + int(p.get("points_awarded") or 0)
except Exception:
    pass

comparison = []
needs_sync = False
for p in profiles:
    uid = p.get("user_id")
    email = p.get("email") or uid
    current = int(p.get("points") or 0)
    correct = int(match_sum.get(uid, 0)) + int(place_sum.get(uid, 0))
    diff = correct - current
    if diff != 0:
        needs_sync = True
    comparison.append({"Uživatel": email, "Aktuální (profiles.points)": current, "Správné (pred+place)": correct, "Rozdíl": diff})

with card("📊 Porovnání"):
    st.dataframe(comparison, use_container_width=True, hide_index=True)

with card("🔄 Akce"):
    if not needs_sync:
        st.success("✅ Vše sedí, není co synchronizovat.")
    else:
        st.warning("⚠️ Nalezeny rozdíly. Klikni na synchronizaci.")
        if st.button("🔄 Synchronizovat", type="primary", use_container_width=True):
            errors = []
            updated = 0
            for p in profiles:
                uid = p.get("user_id")
                correct = int(match_sum.get(uid, 0)) + int(place_sum.get(uid, 0))
                current = int(p.get("points") or 0)
                if correct != current:
                    try:
                        supabase.table("profiles").update({"points": correct}).eq("user_id", uid).execute()
                        updated += 1
                    except Exception as e:
                        errors.append(f"{p.get('email', uid)}: {e}")

            if errors:
                st.error("Některé aktualizace selhaly:")
                st.code("\n".join(errors))
            else:
                st.success(f"✅ Hotovo. Aktualizováno uživatelů: {updated}")
                st.rerun()