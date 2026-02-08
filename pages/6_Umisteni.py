# pages/6_Umisteni.py
import os
import re
from datetime import datetime, timezone, date

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Umístění", page_icon="🏅", layout="wide")

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
    "Umístění",
    "Tipuj číslo (0–99). Tipování je otevřené do dne před soutěží (a do lock_at, pokud je nastaven).",
    image_path="assets/olymp.png",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

NUM_2D_RE = re.compile(r"^\d{1,2}$")

def parse_dt(x: str):
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None

now = datetime.now(timezone.utc)
today = now.date()

def day_label(d: str) -> str:
    try:
        dd = date.fromisoformat(d)
        return dd.strftime("%d.%m.%Y")
    except Exception:
        return str(d)

def can_tip(event: dict) -> tuple[bool, str]:
    ed = event.get("event_date")
    la = event.get("lock_at")

    try:
        event_day = date.fromisoformat(ed) if isinstance(ed, str) else ed
    except Exception:
        event_day = None

    lock_dt = parse_dt(la) if isinstance(la, str) else la

    if event_day is None:
        return False, "Chybný event_date."

    if today >= event_day:
        return False, "Tipování uzavřeno (už je den soutěže nebo po něm)."

    if lock_dt is not None and now >= lock_dt:
        return False, "Tipování uzavřeno (lock_at)."

    return True, "Tipování otevřeno."

# Load events
try:
    ev_res = (
        supabase.table("placement_events")
        .select("id, title, category, event_date, lock_at, correct_value, evaluated_at, created_at")
        .order("event_date")
        .execute()
    )
    events = ev_res.data or []
except Exception as e:
    st.error(f"Nelze načíst placement_events: {e}")
    st.stop()

if not events:
    with card("ℹ️ Info"):
        st.info("Zatím nejsou žádné disciplíny v Umístění.")
    st.stop()

# Load my predictions
try:
    myp_res = (
        supabase.table("placement_predictions")
        .select("event_id, predicted_value, points_awarded, evaluated_at")
        .eq("user_id", user_id)
        .execute()
    )
    my_preds = myp_res.data or []
except Exception as e:
    st.error(f"Nelze načíst tvoje tipy placement_predictions: {e}")
    st.stop()

my_by_event = {p["event_id"]: p for p in my_preds if p.get("event_id") is not None}

future_open, locked, evaluated = [], [], []
for ev in events:
    is_eval = ev.get("evaluated_at") is not None
    ok, _ = can_tip(ev)
    if is_eval:
        evaluated.append(ev)
    elif ok:
        future_open.append(ev)
    else:
        locked.append(ev)

def render_event_card(ev: dict):
    ev_id = ev["id"]
    title = ev.get("title") or "—"
    cat = ev.get("category") or ""
    ed = ev.get("event_date")
    la = ev.get("lock_at")
    eval_at = ev.get("evaluated_at")
    correct = ev.get("correct_value")

    mine = my_by_event.get(ev_id, {})
    my_val = (mine.get("predicted_value") or "").strip()
    my_pts = int(mine.get("points_awarded") or 0)

    ok, msg = can_tip(ev)
    is_eval = eval_at is not None
    has_tip = bool(my_val)

    header = f"{day_label(ed)} — {title}" + (f" ({cat})" if cat else "")

    with card(header, f"{'✅ Natipováno' if has_tip else '❌ Nenatipováno'} • {msg}"):
        if la:
            st.caption(f"🔒 lock_at: {la}")

        if is_eval:
            st.success(f"Vyhodnoceno ✅ Tvoje body: {my_pts}")
            st.markdown(f"**Tvůj tip:** {my_val or '—'}")
            st.markdown(f"**Správně:** {correct or '—'}")
            return

        if has_tip:
            st.info(f"Tvůj aktuální tip: **{my_val}**")

        default_val = my_val if NUM_2D_RE.match(my_val or "") else ""
        user_input = st.text_input(
            "Zadej tip (0–99)",
            value=default_val,
            key=f"tip_{ev_id}",
            max_chars=2,
            disabled=(not ok),
            placeholder="např. 1",
        )

        if st.button("💾 Uložit tip", type="primary", key=f"save_{ev_id}", disabled=(not ok)):
            val = (user_input or "").strip()
            if not val:
                st.error("Vyplň tip.")
            elif not NUM_2D_RE.match(val):
                st.error("Tip musí být číslo 0–99 (max 2 číslice).")
            else:
                try:
                    supabase.table("placement_predictions").upsert(
                        {"user_id": user_id, "event_id": ev_id, "predicted_value": val},
                        on_conflict="user_id,event_id",
                    ).execute()
                    st.success("Tip uložen ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Uložení tipu selhalo: {e}")

with card("🟢 Nadcházející (lze tipovat)"):
    if not future_open:
        st.caption("Nic k tipování.")
    else:
        for ev in future_open:
            render_event_card(ev)

with card("🔒 Uzamčené / probíhající"):
    if not locked:
        st.caption("Nic uzamčeného.")
    else:
        for ev in locked:
            render_event_card(ev)

with card("✅ Vyhodnocené"):
    if not evaluated:
        st.caption("Zatím nic vyhodnoceného.")
    else:
        for ev in evaluated:
            render_event_card(ev)