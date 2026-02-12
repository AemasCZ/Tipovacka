# pages/2_Zapasy.py
import os
from datetime import datetime, timezone
from collections import defaultdict

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

# =====================
# CONFIG
# =====================
load_dotenv()
st.set_page_config(page_title="Zápasy", page_icon="🏒", layout="wide")
apply_o2_style()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ✅ Session pro RLS
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# =====================
# AUTH GUARD + MENU
# =====================
user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

if not user:
    st.warning("Nejsi přihlášený. Jdi na Login.")
    if st.button("Jít na přihlášení", type="primary"):
        st.switch_page("app.py")
    st.stop()

# =====================
# STATE: expandery + potvrzení střelce
# =====================
if "open_days" not in st.session_state:
    st.session_state["open_days"] = set()  # set[str] = "YYYY-MM-DD"
if "pending_scorer_change" not in st.session_state:
    st.session_state["pending_scorer_change"] = None
# { "match_id":..., "old": {...}, "new": {...} }

# =====================
# HELPERS
# =====================
def parse_dt(x: str) -> datetime:
    """ISO string -> aware datetime"""
    if not x:
        return None
    return datetime.fromisoformat(x.replace("Z", "+00:00"))

def fmt_time(dt_utc: datetime) -> str:
    if not dt_utc:
        return "—"
    # necháváme v UTC, aby to bylo konzistentní s DB; pokud chceš lokál, řekni a přidám
    return dt_utc.strftime("%d.%m.%Y %H:%M UTC")

def day_key(dt_utc: datetime) -> str:
    return dt_utc.strftime("%Y-%m-%d") if dt_utc else "unknown"

def is_locked(starts_at_iso: str) -> bool:
    dt = parse_dt(starts_at_iso)
    if not dt:
        return False
    return datetime.now(timezone.utc) >= dt

def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def prediction_keys(match_id: int):
    return (
        f"pred_home_{match_id}",
        f"pred_away_{match_id}",
        f"pred_scorer_id_{match_id}",
        f"pred_scorer_name_{match_id}",
        f"pred_scorer_team_{match_id}",
    )

def save_prediction(match_id: int):
    """Uloží tip (score + scorer) z session_state do DB."""
    k_home, k_away, k_sid, k_sname, k_steam = prediction_keys(match_id)

    payload = {
        "user_id": user["id"],
        "match_id": match_id,
        "home_score": safe_int(st.session_state.get(k_home), 0),
        "away_score": safe_int(st.session_state.get(k_away), 0),
        "scorer_player_id": st.session_state.get(k_sid),
        "scorer_name": st.session_state.get(k_sname),
        "scorer_team": st.session_state.get(k_steam),
    }

    # IMPORTANT: db musí mít UNIQUE (user_id, match_id) pro upsert
    supabase.table("predictions").upsert(payload).execute()

def request_scorer_change(match_id: int, new_id, new_name, new_team):
    """Pokud už je vybraný jiný střelec, otevře potvrzení. Jinak rovnou uloží."""
    k_home, k_away, k_sid, k_sname, k_steam = prediction_keys(match_id)
    cur_id = st.session_state.get(k_sid)
    cur_name = st.session_state.get(k_sname) or "—"
    cur_team = st.session_state.get(k_steam) or "—"

    if not cur_id:
        # rovnou nastav + ulož
        st.session_state[k_sid] = new_id
        st.session_state[k_sname] = new_name
        st.session_state[k_steam] = new_team
        save_prediction(match_id)
        return

    if str(cur_id) == str(new_id):
        return  # kliknul na stejného

    st.session_state["pending_scorer_change"] = {
        "match_id": match_id,
        "old": {"id": cur_id, "name": cur_name, "team": cur_team},
        "new": {"id": new_id, "name": new_name, "team": new_team},
    }
    st.rerun()

def clear_pending():
    st.session_state["pending_scorer_change"] = None

# =====================
# DIALOG: potvrzení změny střelce
# =====================
pending = st.session_state.get("pending_scorer_change")
if pending:
    @st.dialog("Potvrdit změnu střelce")
    def confirm_change():
        old = pending["old"]
        new = pending["new"]

        st.write("Už máš vybraného střelce. Chceš ho změnit?")

        st.table(
            [
                {"": "Aktuální tip", "Střelec": old["name"], "Tým": old["team"]},
                {"": "Nový tip", "Střelec": new["name"], "Tým": new["team"]},
            ]
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Ano, změnit", type="primary", use_container_width=True):
                match_id = pending["match_id"]
                k_home, k_away, k_sid, k_sname, k_steam = prediction_keys(match_id)

                st.session_state[k_sid] = new["id"]
                st.session_state[k_sname] = new["name"]
                st.session_state[k_steam] = new["team"]

                # uložit hned
                try:
                    save_prediction(match_id)
                except Exception as e:
                    st.error(f"Chyba při ukládání tipu: {e}")

                clear_pending()
                st.rerun()

        with c2:
            if st.button("↩️ Nechat původní", use_container_width=True):
                clear_pending()
                st.rerun()

    confirm_change()

# =====================
# HERO
# =====================
render_hero(
    "🏒 Zápasy",
    "Tipuj skóre a střelce. Tipování se zamkne ve chvíli, kdy zápas začne.",
    image_path=None,
)

# =====================
# LOAD MATCHES
# =====================
try:
    matches = (
        supabase.table("matches")
        .select("id, home_team, away_team, starts_at")
        .order("starts_at")
        .execute()
        .data
        or []
    )
except Exception as e:
    st.error(f"Nelze načíst zápasy: {e}")
    st.stop()

if not matches:
    st.info("V databázi nejsou žádné zápasy.")
    st.stop()

match_ids = [m["id"] for m in matches]

# =====================
# LOAD EXISTING PREDICTIONS (current user)
# =====================
pred_map = {}  # match_id -> prediction row
try:
    preds = (
        supabase.table("predictions")
        .select("match_id, home_score, away_score, scorer_player_id, scorer_name, scorer_team")
        .eq("user_id", user["id"])
        .in_("match_id", match_ids)
        .execute()
        .data
        or []
    )
    for p in preds:
        pred_map[p["match_id"]] = p
except Exception:
    pred_map = {}

# =====================
# GROUP MATCHES BY DAY
# =====================
by_day = defaultdict(list)
for m in matches:
    dt = parse_dt(m.get("starts_at"))
    by_day[day_key(dt)].append(m)

# =====================
# RENDER DAYS
# =====================
for day in sorted(by_day.keys()):
    day_matches = by_day[day]
    expanded = day in st.session_state["open_days"]

    with st.expander(f"📅 {day}", expanded=expanded):
        # udrž expander otevřený po uložení
        st.session_state["open_days"].add(day)

        for m in day_matches:
            match_id = m["id"]
            locked = is_locked(m.get("starts_at"))

            # init session defaults for inputs
            k_home, k_away, k_sid, k_sname, k_steam = prediction_keys(match_id)
            if k_home not in st.session_state:
                p = pred_map.get(match_id, {})
                st.session_state[k_home] = safe_int(p.get("home_score"), 0)
                st.session_state[k_away] = safe_int(p.get("away_score"), 0)
                st.session_state[k_sid] = p.get("scorer_player_id")
                st.session_state[k_sname] = p.get("scorer_name")
                st.session_state[k_steam] = p.get("scorer_team")

            with card(
                f"{m['home_team']} vs {m['away_team']}",
                f"🕒 {fmt_time(parse_dt(m.get('starts_at')))}  •  {'🔒 Zamčeno' if locked else '🟢 Otevřeno'}",
            ):
                c1, c2, c3 = st.columns([1, 1, 1.2], gap="large")

                with c1:
                    st.number_input(
                        f"{m['home_team']} (domácí)",
                        min_value=0,
                        max_value=99,
                        step=1,
                        key=k_home,
                        disabled=locked,
                    )

                with c2:
                    st.number_input(
                        f"{m['away_team']} (hosté)",
                        min_value=0,
                        max_value=99,
                        step=1,
                        key=k_away,
                        disabled=locked,
                    )

                with c3:
                    st.write("")
                    st.write("")
                    if st.button(
                        "💾 Uložit tip",
                        type="primary",
                        use_container_width=True,
                        disabled=locked,
                        key=f"save_{match_id}",
                    ):
                        try:
                            save_prediction(match_id)
                            st.success("Uloženo ✅")
                        except Exception as e:
                            st.error(f"Chyba při ukládání: {e}")

                # =====================
                # STŘELCI
                # =====================
                st.divider()
                st.subheader("⚽ Tip na střelce")

                chosen = st.session_state.get(k_sname)
                chosen_team = st.session_state.get(k_steam)
                if st.session_state.get(k_sid):
                    st.info(f"Vybraný střelec: **{chosen}** ({chosen_team})")
                else:
                    st.caption("Zatím nemáš vybraného střelce.")

                # ---- načtení hráčů pro zápas ----
                # POZOR: uprav si název tabulky / view podle toho co máš v DB.
                # Očekávané sloupce: match_id, player_id, player_name, player_team
                try:
                    players = (
                        supabase.table("match_players")
                        .select("player_id, player_name, player_team")
                        .eq("match_id", match_id)
                        .order("player_name")
                        .execute()
                        .data
                        or []
                    )
                except Exception:
                    players = []

                if not players:
                    st.warning(
                        "Pro tento zápas nemám v DB načtené hráče (tabulka/view `match_players`). "
                        "Pokud se jmenuje jinak, řekni mi jak a přepíšu to."
                    )
                    continue

                # ---- render tlačítek ve 3 sloupcích ----
                cols = st.columns(3)
                for i, pl in enumerate(players):
                    pid = pl.get("player_id")
                    pname = pl.get("player_name") or "—"
                    pteam = pl.get("player_team") or "—"

                    is_selected = str(st.session_state.get(k_sid) or "") == str(pid)
                    label = f"{'✅ ' if is_selected else ''}{pname} ({pteam})"

                    with cols[i % 3]:
                        if st.button(
                            label,
                            key=f"pick_{match_id}_{pid}",
                            use_container_width=True,
                            disabled=locked,
                        ):
                            try:
                                request_scorer_change(match_id, pid, pname, pteam)
                            except Exception as e:
                                st.error(f"Chyba: {e}")

                # možnost zrušit střelce
                if st.session_state.get(k_sid):
                    if st.button(
                        "❌ Zrušit střelce",
                        key=f"clear_scorer_{match_id}",
                        disabled=locked,
                    ):
                        st.session_state[k_sid] = None
                        st.session_state[k_sname] = None
                        st.session_state[k_steam] = None
                        try:
                            save_prediction(match_id)
                            st.success("Střelec zrušen ✅")
                        except Exception as e:
                            st.error(f"Chyba při ukládání: {e}")