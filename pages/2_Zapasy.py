# pages/2_Zapasy.py
import os
import re
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Zápasy", page_icon="🏒", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Session pro RLS
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

apply_o2_style()

user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Zápasy",
    "Tipuj výsledek a střelce. Klik na hráče uloží střelce okamžitě.",
    image_path="assets/olympic.jpeg",
)

# Guard login
if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený. Jdi na Login.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# ----- Helpers -----
# ⚠️ DŮLEŽITÉ: starts_at je v DB uložené jako timestamptz, ale časy byly zadávané jako lokální.
# Proto ho interpretujeme jako Europe/Prague (CET/CEST) a teprve potom převádíme na UTC pro lock.
EVENT_TZ = ZoneInfo("Europe/Prague")

def parse_dt(x: str):
    try:
        raw = datetime.fromisoformat(x.replace("Z", "+00:00"))
        # vezmeme "hodiny:minuty" jako lokální čas eventu
        local = raw.replace(tzinfo=EVENT_TZ)
        return local.astimezone(timezone.utc)
    except Exception:
        return None

def iso2_flag(iso2: str) -> str:
    if not iso2 or len(iso2) != 2:
        return "🏳️"
    iso2 = iso2.upper()
    return "".join(chr(ord(c) + 127397) for c in iso2)

def safe_get(d: dict, key: str, default=None):
    try:
        return d.get(key, default)
    except Exception:
        return default

def chunks(lst, n=3):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def clean_name(x: str) -> str:
    if not x:
        return ""
    return x.strip().lstrip(",").strip()

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
def is_uuid(x) -> bool:
    if not x:
        return False
    return bool(UUID_RE.match(str(x)))

COUNTRY_NAME_TO_ISO2 = {
    "Canada": "CA", "Kanada": "CA",
    "United States": "US", "USA": "US", "United States of America": "US", "Spojené státy": "US",
    "Sweden": "SE", "Švédsko": "SE", "Svedsko": "SE",
    "Finland": "FI", "Finsko": "FI",
    "Czechia": "CZ", "Czech Republic": "CZ", "Česko": "CZ", "Cesko": "CZ",
    "Slovakia": "SK", "Slovensko": "SK",
    "Russia": "RU", "Rusko": "RU",
    "Switzerland": "CH", "Švýcarsko": "CH", "Svycarsko": "CH",
    "Germany": "DE", "Německo": "DE", "Nemecko": "DE",
    "Latvia": "LV", "Lotyšsko": "LV", "Lotyssko": "LV",
    "Denmark": "DK", "Dánsko": "DK", "Dansko": "DK",
    "Norway": "NO", "Norsko": "NO",
    "Austria": "AT", "Rakousko": "AT",
    "France": "FR", "Francie": "FR",
    "Belarus": "BY", "Bělorusko": "BY", "Belorusko": "BY",
    "Kazakhstan": "KZ", "Kazachstán": "KZ", "Kazachstan": "KZ",
    "Slovenia": "SI", "Slovinsko": "SI",
    "Italy": "IT", "Itálie": "IT", "Italie": "IT",
    "Japan": "JP", "Japonsko": "JP",
    "South Korea": "KR", "Korea": "KR", "Jižní Korea": "KR", "Jizni Korea": "KR",
    "China": "CN", "Čína": "CN", "Cina": "CN",
    "Great Britain": "GB", "United Kingdom": "GB", "Velká Británie": "GB", "Velka Britanie": "GB",
    "Hungary": "HU", "Maďarsko": "HU", "Madarsko": "HU",
    "Poland": "PL", "Polsko": "PL",
    "Ukraine": "UA", "Ukrajina": "UA",
    "Lithuania": "LT", "Litva": "LT",
    "Netherlands": "NL", "Nizozemsko": "NL",
    "Estonia": "EE", "Estonsko": "EE",
    "Romania": "RO", "Rumunsko": "RO",
    "Croatia": "HR", "Chorvatsko": "HR",
}
COUNTRY3_TO_ISO2 = {
    "CAN": "CA", "USA": "US", "SWE": "SE", "FIN": "FI", "CZE": "CZ", "SVK": "SK", "RUS": "RU",
    "SUI": "CH", "GER": "DE", "LAT": "LV", "DEN": "DK", "NOR": "NO", "AUT": "AT", "FRA": "FR",
    "BLR": "BY", "KAZ": "KZ", "SLO": "SI", "ITA": "IT", "JPN": "JP", "KOR": "KR", "CHN": "CN",
    "GBR": "GB", "HUN": "HU", "POL": "PL", "UKR": "UA", "NED": "NL", "EST": "EE", "ROU": "RO",
    "CRO": "HR", "LTU": "LT",
}

def team_flag(team_name: str) -> str:
    iso2 = COUNTRY_NAME_TO_ISO2.get(team_name)
    return iso2_flag(iso2) if iso2 else "🏳️"

def club_country_flag(country3: str | None) -> str:
    if not country3:
        return "🏳️"
    iso2 = COUNTRY3_TO_ISO2.get(country3.upper())
    return iso2_flag(iso2) if iso2 else "🏳️"

now = datetime.now(timezone.utc)
today = now.date()

def day_label(d: date):
    return d.strftime("%d.%m.%Y")

# ----- DB: matches -----
matches_res = (
    supabase.table("matches")
    .select("id, home_team, away_team, starts_at, final_home_score, final_away_score")
    .order("starts_at")
    .execute()
)
matches = matches_res.data or []
if not matches:
    with card("ℹ️ Info"):
        st.info("V databázi nejsou žádné zápasy.")
    st.stop()

def load_my_predictions():
    try:
        res = (
            supabase.table("predictions")
            .select("match_id, home_score, away_score, scorer_player_id, scorer_name, scorer_flag, scorer_team")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []
    except Exception:
        res = (
            supabase.table("predictions")
            .select("match_id, home_score, away_score")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []

preds = load_my_predictions()
pred_by_match = {p["match_id"]: p for p in preds}

by_day = {}
for m in matches:
    dt = parse_dt(m["starts_at"])
    if not dt:
        continue
    m["_dt"] = dt
    d = dt.date()
    by_day.setdefault(d, []).append(m)

days_sorted = sorted(by_day.keys())
future_days = [d for d in days_sorted if d >= today]
past_days = [d for d in days_sorted if d < today]

OPEN_DAY_KEY = "open_day"

@st.cache_data(ttl=120)
def load_players_for_team(team_name: str):
    try:
        res = (
            supabase.table("players")
            .select("id, team_name, full_name, role, club_name, country3, league_country3")
            .eq("team_name", team_name)
            .order("role")
            .order("full_name")
            .execute()
        )
        return res.data or []
    except Exception:
        try:
            res = (
                supabase.table("players")
                .select("team_name, full_name, role")
                .eq("team_name", team_name)
                .order("role")
                .order("full_name")
                .execute()
            )
            return res.data or []
        except Exception:
            return []

def upsert_base_prediction(match_id: str, home_score: int, away_score: int):
    supabase.table("predictions").upsert(
        {"user_id": user_id, "match_id": match_id, "home_score": int(home_score), "away_score": int(away_score)},
        on_conflict="user_id,match_id"
    ).execute()

def update_scorer(match_id: str, scorer_payload: dict):
    supabase.table("predictions").update(scorer_payload).eq("user_id", user_id).eq("match_id", match_id).execute()

def save_scorer(match_id: str, player: dict, team_name: str, match_day: date):
    current_home = int(st.session_state.get(f"h_{match_id}", pred_by_match.get(match_id, {}).get("home_score", 0) or 0))
    current_away = int(st.session_state.get(f"a_{match_id}", pred_by_match.get(match_id, {}).get("away_score", 0) or 0))

    full_name = clean_name(safe_get(player, "full_name", "Neznámý hráč"))
    raw_player_id = safe_get(player, "id")
    scorer_player_id = str(raw_player_id) if is_uuid(raw_player_id) else None

    scorer_payload = {
        "scorer_player_id": scorer_player_id,
        "scorer_name": full_name,
        "scorer_flag": team_flag(team_name),
        "scorer_team": team_name,
    }

    try:
        upsert_base_prediction(match_id, current_home, current_away)
        update_scorer(match_id, scorer_payload)
        st.session_state[OPEN_DAY_KEY] = match_day.isoformat()
        st.success(f"Střelec uložen ✅ {scorer_payload['scorer_flag']} {full_name}")
        st.rerun()
    except Exception as e:
        st.error("Uložení střelce selhalo:")
        st.code(str(e))

def player_label(p: dict):
    full_name = clean_name(safe_get(p, "full_name", "Neznámý hráč"))
    club = safe_get(p, "club_name", "") or "—"
    league_c3 = safe_get(p, "league_country3", "") or safe_get(p, "country3", "")
    cf = club_country_flag(league_c3)
    return f"{full_name}\n({club} {cf})"

def render_team_players_full(team_name: str, match_id: str, side: str, match_day: date):
    players = load_players_for_team(team_name)
    atts = [p for p in players if safe_get(p, "role") == "ATT"]
    defs = [p for p in players if safe_get(p, "role") == "DEF"]

    # Aktuální střelec pro tento zápas
    current_scorer_name = pred_by_match.get(match_id, {}).get("scorer_name")

    # Klíč pro čekající potvrzení (uložen v session_state)
    confirm_key = f"confirm_scorer_{match_id}"

    def pick_player(p, tm, role_tag):
        pid = safe_get(p, "id") or f"{tm}:{clean_name(safe_get(p,'full_name',''))}:{role_tag}"
        if col.button(player_label(p), key=f"pick_{match_id}_{side}_{role_tag}_{pid}", type="secondary", use_container_width=True):
            if current_scorer_name:
                # Střelec už existuje → ulož do session_state a čekej na potvrzení
                st.session_state[confirm_key] = {
                    "match_id": match_id,
                    "player": p,
                    "team_name": tm,
                    "match_day": match_day,
                }
                st.rerun()
            else:
                # Žádný střelec → uložit rovnou
                save_scorer(match_id, p, tm, match_day)

    st.markdown(f"**{team_flag(team_name)} {team_name}**")
    st.markdown("**Útočníci:**")
    if not atts:
        st.caption("— žádní útočníci v DB —")
    else:
        for row in chunks(atts, 3):
            cols = st.columns(3)
            for col, p in zip(cols, row):
                pick_player(p, team_name, "ATT")

    st.write("")
    st.markdown("**Obránci:**")
    if not defs:
        st.caption("— žádní obránci v DB —")
    else:
        for row in chunks(defs, 3):
            cols = st.columns(3)
            for col, p in zip(cols, row):
                pick_player(p, team_name, "DEF")

def render_scorers_section(match_id: str, home_team: str, away_team: str, match_day: date):
    confirm_key = f"confirm_scorer_{match_id}"

    # Potvrzovaci dialog – jednou pres celou sirku
    if confirm_key in st.session_state:
        pending = st.session_state[confirm_key]
        new_name = clean_name(safe_get(pending["player"], "full_name", "Neznamy hrac"))
        new_flag = team_flag(pending["team_name"])
        current_scorer_name = pred_by_match.get(match_id, {}).get("scorer_name")
        old_flag = pred_by_match.get(match_id, {}).get("scorer_flag", "🏳️")

        st.markdown(
            f"""
            <div style="background:#fff3cd;border:2px solid #f0a500;border-radius:12px;padding:20px 24px;margin-bottom:16px;">
                <p style="font-size:1.2rem;font-weight:700;margin:0 0 12px 0;">⚠️ Chceš změnit střelce?</p>
                <p style="font-size:1.05rem;margin:4px 0;">
                    <span style="color:#555;">Stávající:</span>&nbsp;
                    <strong>{old_flag} {current_scorer_name}</strong>
                </p>
                <p style="font-size:1.05rem;margin:4px 0;">
                    <span style="color:#555;">Nový:</span>&nbsp;
                    <strong>{new_flag} {new_name}</strong>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_yes, col_no, _ = st.columns([1, 1, 2])
        with col_yes:
            if st.button("✅ Potvrdit změnu", key=f"confirm_yes_{match_id}", type="primary", use_container_width=True):
                p_pending = st.session_state.pop(confirm_key)
                save_scorer(p_pending["match_id"], p_pending["player"], p_pending["team_name"], p_pending["match_day"])
        with col_no:
            if st.button("❌ Zrušit", key=f"confirm_no_{match_id}", use_container_width=True):
                del st.session_state[confirm_key]
                st.rerun()
        return  # Hrace nezobrazuj, dokud uzivatel nerozhodne

    left, right = st.columns(2)
    with left:
        render_team_players_full(home_team, match_id, side="home", match_day=match_day)
    with right:
        render_team_players_full(away_team, match_id, side="away", match_day=match_day)

def match_card(m: dict):
    match_id = m["id"]
    dt = m["_dt"]
    match_day = dt.date()
    time_str = dt.strftime("%H:%M")

    p = pred_by_match.get(match_id, {})
    has_tip = match_id in pred_by_match
    status = f"✅ Natipováno ({p.get('home_score', 0)} : {p.get('away_score', 0)})" if has_tip else "⏳ Chybí tip"

    scorer_name = p.get("scorer_name")
    scorer_flag = p.get("scorer_flag")
    scorer_team = p.get("scorer_team")

    with card(
        f"{team_flag(m['home_team'])} {m['home_team']}  vs  {team_flag(m['away_team'])} {m['away_team']}",
        f"⏰ Začátek: {time_str} • {status}",
    ):
        if scorer_name:
            st.markdown(f"**Střelec:** {scorer_flag or '🏳️'} {scorer_name} ({scorer_team})")
        else:
            st.markdown("**Střelec:** —")

        if dt <= now:
            final_home = m.get("final_home_score")
            final_away = m.get("final_away_score")
            if final_home is not None and final_away is not None:
                st.markdown(
                    f"""
                    <div style="display:inline-block;background:#1b4cff;color:#fff;
                                border-radius:12px;padding:8px 20px;font-size:1.15rem;
                                font-weight:800;letter-spacing:0.02em;margin-bottom:6px;">
                        🏒 Výsledek: {int(final_home)} : {int(final_away)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("Zápas proběhl – výsledek zatím nezadán.")
            return

        st.markdown("### 📝 Tip na výsledek")
        c1, c2, c3 = st.columns([1, 1, 1.1], vertical_alignment="bottom")

        default_home = int(p.get("home_score", 0) or 0)
        default_away = int(p.get("away_score", 0) or 0)

        with c1:
            home_score = st.number_input(f"{m['home_team']} (góly)", 0, 30, default_home, key=f"h_{match_id}")
        with c2:
            away_score = st.number_input(f"{m['away_team']} (góly)", 0, 30, default_away, key=f"a_{match_id}")

        with c3:
            if st.button("💾 Uložit tip", key=f"save_{match_id}", type="primary", use_container_width=True):
                try:
                    upsert_base_prediction(match_id, int(home_score), int(away_score))

                    # zachovej střelce
                    if p.get("scorer_name"):
                        try:
                            update_scorer(match_id, {
                                "scorer_player_id": p.get("scorer_player_id"),
                                "scorer_name": p.get("scorer_name"),
                                "scorer_flag": p.get("scorer_flag"),
                                "scorer_team": p.get("scorer_team"),
                            })
                        except Exception:
                            pass

                    st.session_state[OPEN_DAY_KEY] = match_day.isoformat()
                    st.success("Tip uložen ✅")
                    st.rerun()
                except Exception as e:
                    st.error("Uložení tipu selhalo:")
                    st.code(str(e))

        st.markdown("### ⚽ Tip na střelce")
        if scorer_name:
            st.markdown(f"✅ **Zvolený:** {scorer_flag or '🏳️'} {scorer_name} ({scorer_team})")
        else:
            st.caption("Zatím nevybrán žádný střelec.")

        st.info("Klik na hráče = okamžité uložení střelce.")
        render_scorers_section(match_id, m["home_team"], m["away_team"], match_day=match_day)

# ----- UI -----
with card("📅 Nadcházející zápasy", "Rozklikni den a natipuj vše před začátkem."):
    if not future_days:
        st.info("Žádné nadcházející dny.")
    else:
        for d in future_days:
            ms = by_day[d]
            total = len(ms)
            done = sum(1 for mm in ms if mm["id"] in pred_by_match)
            day_key = d.isoformat()
            is_open = st.session_state.get(OPEN_DAY_KEY) == day_key
            with st.expander(f"{day_label(d)} • Natipováno {done}/{total}", expanded=is_open):
                for mm in ms:
                    match_card(mm)

with card("🕘 Odehrané", "Pouze náhled. Tipování je uzavřené."):
    if not past_days:
        st.info("Zatím nic odehraného.")
    else:
        for d in reversed(past_days):
            ms = by_day[d]
            total = len(ms)
            done = sum(1 for mm in ms if mm["id"] in pred_by_match)
            day_key = d.isoformat()
            is_open = st.session_state.get(OPEN_DAY_KEY) == day_key
            with st.expander(f"{day_label(d)} • Natipováno {done}/{total}", expanded=is_open):
                for mm in ms:
                    match_card(mm)