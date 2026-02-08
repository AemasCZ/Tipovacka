# pages/7_Admin_Umisteni.py
import os
import re
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Admin – Vyhodnocení umístění", page_icon="🛠️", layout="wide")

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
    "Admin – Vyhodnocení umístění",
    "Nastavíš správnou hodnotu a systém rozdá body do placement_predictions.points_awarded (10/0).",
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

NUM_2D_RE = re.compile(r"^\d{1,2}$")

def fmt_date(d) -> str:
    try:
        if isinstance(d, str):
            dt = datetime.fromisoformat(d + "T00:00:00+00:00")
        else:
            dt = d
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(d)

events = (supabase.table("placement_events").select(
    "id, title, category, event_date, lock_at, correct_value, evaluated_at, created_at"
).order("event_date", desc=True).execute().data or [])

if not events:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádné placement eventy.")
    st.stop()

event_options = []
event_by_label = {}
for ev in events:
    title = ev.get("title") or "—"
    cat = ev.get("category") or ""
    ed = ev.get("event_date")
    is_eval = ev.get("evaluated_at") is not None
    correct = ev.get("correct_value")
    status = "✅ vyhodnoceno" if is_eval else "🕒 nevyhodnoceno"
    extra = f" · správně: {correct}" if (is_eval and correct is not None) else ""
    label = f"{fmt_date(ed)} — {title}" + (f" ({cat})" if cat else "") + f" · {status}{extra}"
    event_options.append(label)
    event_by_label[label] = ev

selected_label = st.selectbox("Vyber event", event_options, index=0)
selected = event_by_label[selected_label]
selected_event_id = selected["id"]

preds = (supabase.table("placement_predictions").select(
    "user_id, event_id, predicted_value, points_awarded, evaluated_at"
).eq("event_id", selected_event_id).execute().data or [])

emails_by_user = {}
user_ids = sorted({p["user_id"] for p in preds if p.get("user_id")})
if user_ids:
    try:
        profs = supabase.table("profiles").select("user_id, email").in_("user_id", user_ids).execute().data or []
        emails_by_user = {x["user_id"]: (x.get("email") or "—") for x in profs}
    except Exception:
        emails_by_user = {}

is_eval = selected.get("evaluated_at") is not None
correct_value_existing = selected.get("correct_value")

with card("📌 Event"):
    st.markdown(f"**{selected.get('title') or '—'}**")
    st.caption(f"📅 {fmt_date(selected.get('event_date'))} • Kategorie: {selected.get('category') or '—'}")
    st.info(f"Stav: {'✅ vyhodnoceno' if is_eval else '🕒 nevyhodnoceno'}")

with card("✅ Vyhodnocení"):
    cA, cB, cC = st.columns([1.2, 1.2, 1.6], vertical_alignment="bottom")

    with cA:
        correct_value = st.number_input(
            "Správná hodnota (0–99)",
            min_value=0,
            max_value=99,
            value=int(correct_value_existing) if str(correct_value_existing).isdigit() else 0,
            step=1,
        )

    with cB:
        do_eval = st.button("✅ Vyhodnotit", type="primary", use_container_width=True)

    with cC:
        do_reset = st.button("♻️ Reset", type="secondary", use_container_width=True)

    if do_eval:
        cv = str(int(correct_value)).strip()
        if not NUM_2D_RE.match(cv):
            st.error("Správná hodnota musí být 0–99.")
            st.stop()

        try:
            now_iso = datetime.now(timezone.utc).isoformat()

            supabase.table("placement_events").update({"correct_value": cv, "evaluated_at": now_iso}).eq("id", selected_event_id).execute()

            preds2 = (supabase.table("placement_predictions").select("user_id, predicted_value").eq("event_id", selected_event_id).execute().data or [])
            updated = 0
            for p in preds2:
                pv = (p.get("predicted_value") or "").strip()
                if not pv:
                    continue
                pts = 10 if pv == cv else 0
                supabase.table("placement_predictions").update({"points_awarded": pts, "evaluated_at": now_iso}).eq("event_id", selected_event_id).eq("user_id", p["user_id"]).execute()
                updated += 1

            st.success(f"Hotovo ✅ Aktualizováno tipů: {updated}")
            st.rerun()

        except Exception as e:
            st.error(f"Vyhodnocení selhalo: {e}")

    if do_reset:
        try:
            supabase.table("placement_events").update({"correct_value": None, "evaluated_at": None}).eq("id", selected_event_id).execute()
            supabase.table("placement_predictions").update({"points_awarded": 0, "evaluated_at": None}).eq("event_id", selected_event_id).execute()
            st.success("Reset hotov ♻️")
            st.rerun()
        except Exception as e:
            st.error(f"Reset selhal: {e}")

with card("📋 Tipy uživatelů"):
    if not preds:
        st.caption("Zatím nikdo netipoval.")
    else:
        rows = []
        correct_str = str(correct_value_existing).strip() if correct_value_existing is not None else None
        for p in preds:
            uid = p.get("user_id")
            email = emails_by_user.get(uid, "—")
            pv = (p.get("predicted_value") or "").strip()
            pts = int(p.get("points_awarded") or 0)
            ok = (correct_str is not None and pv == correct_str)
            rows.append({"email": email, "tip": pv, "správně": "✅" if ok else ("—" if correct_str is None else "❌"), "body": pts})

        rows.sort(key=lambda x: (x["správně"] != "✅", -x["body"], x["email"]))
        st.dataframe(rows, use_container_width=True, hide_index=True)