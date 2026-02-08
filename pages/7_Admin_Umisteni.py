import os
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Admin – Vyhodnocení umístění", page_icon="🛠️", layout="wide")

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
        hr { border: none; border-top: 1px solid rgba(255,255,255,0.10); margin: 14px 0; }
        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
        .pill {
            display:inline-flex; align-items:center; gap:8px;
            padding:6px 10px; border-radius:999px;
            border:1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            font-size: 13px; font-weight: 800;
            white-space: nowrap;
        }
        .pill-ok { border-color: rgba(0,255,0,0.22); background: rgba(0,255,0,0.06); }
        .pill-warn { border-color: rgba(255,180,0,0.22); background: rgba(255,180,0,0.06); }
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
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# =====================
# Ověření admina
# =====================
try:
    prof = (
        supabase.table("profiles")
        .select("user_id, email, is_admin")
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    profile = prof.data
except Exception as e:
    st.error(f"Nelze načíst profil: {e}")
    st.stop()

if not profile or not profile.get("is_admin"):
    st.error("Tato stránka je jen pro admina.")
    st.stop()

# =====================
# Helpery
# =====================
def fmt_date(d) -> str:
    try:
        if isinstance(d, str):
            # očekává YYYY-MM-DD
            dt = datetime.fromisoformat(d + "T00:00:00+00:00")
        else:
            dt = d
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(d)

now = datetime.now(timezone.utc)

# =====================
# Načtení eventů
# =====================
try:
    ev_res = (
        supabase.table("placement_events")
        .select("id, title, category, event_date, lock_at, correct_value, evaluated_at, created_at")
        .order("event_date", desc=True)
        .execute()
    )
    events = ev_res.data or []
except Exception as e:
    st.error(f"Nelze načíst placement_events: {e}")
    st.stop()

st.title("🛠️ Admin – Vyhodnocení umístění")
st.caption("Vybereš event, nastavíš správnou hodnotu a systém rozdá 10 bodů za správný tip (jinak 0).")

if not events:
    st.info("Zatím nejsou žádné placement eventy.")
    st.stop()

# =====================
# Dropdown eventů
# =====================
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
event_id = selected["id"]

# =====================
# Načtení tipů pro vybraný event
# =====================
try:
    pred_res = (
        supabase.table("placement_predictions")
        .select("user_id, event_id, predicted_value, points_awarded, evaluated_at")
        .eq("event_id", event_id)
        .execute()
    )
    preds = pred_res.data or []
except Exception as e:
    st.error(f"Nelze načíst placement_predictions pro event: {e}")
    st.stop()

# profily (email) pro user_id z tipů
emails_by_user = {}
user_ids = sorted({p["user_id"] for p in preds if p.get("user_id")})
if user_ids:
    try:
        profs_res = (
            supabase.table("profiles")
            .select("user_id, email")
            .in_("user_id", user_ids)
            .execute()
        )
        profs = profs_res.data or []
        emails_by_user = {x["user_id"]: (x.get("email") or "—") for x in profs}
    except Exception:
        emails_by_user = {}

# =====================
# UI karta
# =====================
is_eval = selected.get("evaluated_at") is not None
correct_value_existing = selected.get("correct_value")

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(f'<div class="title">{selected.get("title") or "—"}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="muted">📅 Datum: <b>{fmt_date(selected.get("event_date"))}</b>'
    + (f' · 🏷️ Kategorie: <b>{selected.get("category")}</b>' if selected.get("category") else "")
    + "</div>",
    unsafe_allow_html=True,
)

if is_eval:
    st.markdown(
        f'<div class="pill pill-ok">✅ Vyhodnoceno · správně: <b>{correct_value_existing}</b></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="pill pill-warn">🕒 Nevyhodnoceno</div>', unsafe_allow_html=True)

st.markdown("<hr/>", unsafe_allow_html=True)

# =====================
# Zadání správné hodnoty + akce
# =====================
colA, colB, colC = st.columns([1.2, 1.2, 1.6], vertical_alignment="top")

with colA:
    correct_value = st.number_input(
        "Správná hodnota (0–99)",
        min_value=0,
        max_value=99,
        value=int(correct_value_existing) if str(correct_value_existing).isdigit() else 0,
        step=1,
        disabled=False,
    )

with colB:
    st.write(" ")
    st.write(" ")
    do_eval = st.button("✅ Vyhodnotit a rozdat body", type="primary", use_container_width=True, disabled=False)

with colC:
    st.write(" ")
    st.write(" ")
    do_reset = st.button("♻️ Reset vyhodnocení (vrátit zpět)", type="secondary", use_container_width=True)

# =====================
# Vyhodnocení
# =====================
if do_eval:
    try:
        # 1) uložit do placement_events mental model: correct_value + evaluated_at
        supabase.table("placement_events").update(
            {
                "correct_value": str(int(correct_value)),
                "evaluated_at": now.isoformat(),
            }
        ).eq("id", event_id).execute()

        # 2) přepočítat body pro všechny tipy v tomto eventu
        # znovu načteme preds (ať pracujeme s fresh daty)
        pred_res2 = (
            supabase.table("placement_predictions")
            .select("user_id, event_id, predicted_value")
            .eq("event_id", event_id)
            .execute()
        )
        preds2 = pred_res2.data or []

        updates = []
        correct_str = str(int(correct_value))

        for p in preds2:
            pv = (p.get("predicted_value") or "").strip()
            pts = 10 if pv == correct_str else 0
            updates.append(
                {
                    "user_id": p["user_id"],
                    "event_id": p["event_id"],
                    "points_awarded": pts,
                    "evaluated_at": now.isoformat(),
                }
            )

        if updates:
            supabase.table("placement_predictions").upsert(
                updates,
                on_conflict="user_id,event_id"
            ).execute()

        st.success("Vyhodnoceno ✅ Body přiděleny (10 / 0) podle správnosti tipu.")
        st.info("Pokud leaderboard bere body z tabulky profiles, spusť ještě svůj 'sync bodů' krok (pokud ho používáš).")
        st.rerun()

    except Exception as e:
        st.error(f"Vyhodnocení selhalo: {e}")

# =====================
# Reset vyhodnocení
# =====================
if do_reset:
    try:
        supabase.table("placement_events").update(
            {
                "correct_value": None,
                "evaluated_at": None,
            }
        ).eq("id", event_id).execute()

        # u tipů vynulujeme body + evaluated_at
        supabase.table("placement_predictions").update(
            {
                "points_awarded": 0,
                "evaluated_at": None,
            }
        ).eq("event_id", event_id).execute()

        st.success("Reset hotov ♻️ (event i body u tipů vráceny zpět).")
        st.rerun()

    except Exception as e:
        st.error(f"Reset selhal: {e}")

# =====================
# Přehled tipů
# =====================
st.subheader("📋 Tipy uživatelů pro tento event")

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
        rows.append(
            {
                "email": email,
                "tip": pv,
                "správně": "✅" if ok else ("—" if correct_str is None else "❌"),
                "body": pts,
            }
        )

    # hezky seřadit (nejdřív správní, pak body)
    rows.sort(key=lambda x: (x["správně"] != "✅", -x["body"], x["email"]))

    st.dataframe(rows, use_container_width=True, hide_index=True)

st.markdown("</div>", unsafe_allow_html=True)