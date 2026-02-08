import os
import re
from datetime import datetime, timezone, date

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Umístění", page_icon="🏅", layout="wide")

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
        .title { font-size: 22px; font-weight: 900; margin: 0 0 6px 0; }
        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
        hr { border: none; border-top: 1px solid rgba(255,255,255,0.10); margin: 14px 0; }
    </style>
    """,
    unsafe_allow_html=True
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

# ✅ Navázání session (nutné pro RLS)
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
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# =====================
# Pomocné
# =====================
NUM_2D_RE = re.compile(r"^\d{1,2}$")  # 1–2 číslice

def parse_dt(x: str):
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None

now = datetime.now(timezone.utc)
today = now.date()

# =====================
# Načtení eventů
# =====================
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
    st.info("Zatím nejsou žádné disciplíny v Umístění.")
    st.stop()

# =====================
# Načtení mých tipů
# =====================
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

# =====================
# Logika tipování:
# - tipovat lze jen pokud je dnes < event_date
# - a zároveň now < lock_at (pokud máš lock_at nastavené)
# =====================
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

    # tvoje zadání: pokud už je datum soutěže, tipovat nepůjde
    if today >= event_day:
        return False, "Tipování uzavřeno (už je den soutěže nebo po něm)."

    # navíc lock_at (pokud existuje)
    if lock_dt is not None and now >= lock_dt:
        return False, "Tipování uzavřeno (lock_at)."

    return True, "Tipování otevřeno."

def day_label(d: str) -> str:
    try:
        dd = date.fromisoformat(d)
        return dd.strftime("%d.%m.%Y")
    except Exception:
        return str(d)

# =====================
# UI
# =====================
st.title("🏅 Umístění")
st.caption("Tipuješ číslo (umístění / počet). Pole je omezené na max 2 číslice (0–99). Tipovat lze jen do dne před soutěží (a do lock_at, pokud je nastaven).")

# Rozdělení do sekcí
future_open = []
locked = []
evaluated = []

for ev in events:
    is_eval = ev.get("evaluated_at") is not None
    ok, _ = can_tip(ev)
    if is_eval:
        evaluated.append(ev)
    elif ok:
        future_open.append(ev)
    else:
        locked.append(ev)

# =====================
# Render jedné karty
# =====================
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

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(f'<div class="title">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="muted">📅 Datum: <b>{day_label(ed)}</b>'
        + (f' · 🏷️ Kategorie: <b>{cat}</b>' if cat else "")
        + "</div>",
        unsafe_allow_html=True
    )

    if la:
        st.markdown(f'<div class="muted">🔒 lock_at: {la}</div>', unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Stav
    if is_eval:
        st.success(f"✅ Vyhodnoceno · Tvoje body: {my_pts}")
        st.markdown(f"**Tvůj tip:** {my_val or '—'}")
        st.markdown(f"**Správně:** {correct or '—'}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if ok:
        st.info(f"🟢 {msg}")
    else:
        st.warning(f"🔒 {msg}")

    # Pole max 2 číslice (0–99)
    # max_chars = 2 zaručí „prostor jen na 2 číslice“
    default_val = my_val if NUM_2D_RE.match(my_val or "") else ""

    user_input = st.text_input(
        "Tvůj tip (0–99)",
        value=default_val,
        key=f"tip_{ev_id}",
        max_chars=2,
        disabled=(not ok),
        placeholder="např. 1"
    )

    # Uložit
    if st.button("💾 Uložit tip", type="primary", key=f"save_{ev_id}", disabled=(not ok)):
        val = (user_input or "").strip()

        if not val:
            st.error("Vyplň tip.")
        elif not NUM_2D_RE.match(val):
            st.error("Tip musí být číslo 0–99 (max 2 číslice).")
        else:
            try:
                payload = {
                    "user_id": user_id,
                    "event_id": ev_id,
                    "predicted_value": val,  # ukládáme jako text
                }
                supabase.table("placement_predictions").upsert(
                    payload,
                    on_conflict="user_id,event_id"
                ).execute()

                st.success("Tip uložen ✅")
                st.rerun()

            except Exception as e:
                st.error(f"Uložení tipu selhalo: {e}")

    if my_val:
        st.markdown(f"**Uložený tip:** {my_val}")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Sekce
# =====================
st.subheader("🟢 Nadcházející (lze tipovat)")
if not future_open:
    st.caption("Nic k tipování.")
else:
    for ev in future_open:
        render_event_card(ev)

st.subheader("🔒 Uzamčené / probíhhající")
if not locked:
    st.caption("Nic uzamčeného.")
else:
    for ev in locked:
        render_event_card(ev)

st.subheader("✅ Vyhodnocené")
if not evaluated:
    st.caption("Zatím nic vyhodnoceného.")
else:
    for ev in evaluated:
        render_event_card(ev)