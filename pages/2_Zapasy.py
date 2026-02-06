import os
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv


# =====================
# CSS (dark + drobný styling tlačítek v pickeru)
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }

        .picker-title {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .picker-subtitle {
            font-size: 13px;
            opacity: 0.8;
            margin-top: -4px;
            margin-bottom: 10px;
        }
        .picker-section {
            font-size: 14px;
            font-weight: 700;
            margin-top: 10px;
            margin-bottom: 6px;
            opacity: 0.95;
        }
        .picker-gap {
            height: 10px;
        }

        /* trochu zmenšit Streamlit buttony v seznamu hráčů */
        div.stButton > button {
            width: 100%;
            text-align: left;
            padding: 10px 12px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================
# Flag helpers (30 hokejových zemí – ISO3 -> ISO2 -> emoji)
# =====================
TOP_HOCKEY_ISO3_TO_ISO2 = {
    "CAN": "CA",
    "USA": "US",
    "SWE": "SE",
    "FIN": "FI",
    "RUS": "RU",
    "CZE": "CZ",
    "SVK": "SK",
    "SUI": "CH",
    "GER": "DE",
    "LAT": "LV",
    "DEN": "DK",
    "NOR": "NO",
    "AUT": "AT",
    "FRA": "FR",
    "BLR": "BY",
    "KAZ": "KZ",
    "SLO": "SI",
    "ITA": "IT",
    "POL": "PL",
    "HUN": "HU",
    "GBR": "GB",
    "JPN": "JP",
    "KOR": "KR",
    "CHN": "CN",
    "NED": "NL",
    "ROU": "RO",
    "EST": "EE",
    "UKR": "UA",
    "CRO": "HR",
    "SRB": "RS",
}

# mapování názvů zemí (CZ + EN) -> ISO3 (pro vlajku nároďáku v UI)
TEAM_NAME_TO_ISO3 = {
    # CZ názvy
    "Kanada": "CAN",
    "USA": "USA",
    "Spojené státy": "USA",
    "Švédsko": "SWE",
    "Finsko": "FIN",
    "Rusko": "RUS",
    "Česko": "CZE",
    "Česká republika": "CZE",
    "Slovensko": "SVK",
    "Švýcarsko": "SUI",
    "Německo": "GER",
    "Lotyšsko": "LAT",
    "Dánsko": "DEN",
    "Norsko": "NOR",
    "Rakousko": "AUT",
    "Francie": "FRA",
    "Bělorusko": "BLR",
    "Kazachstán": "KAZ",
    "Slovinsko": "SLO",
    "Itálie": "ITA",
    "Polsko": "POL",
    "Maďarsko": "HUN",
    "Velká Británie": "GBR",
    "Japonsko": "JPN",
    "Jižní Korea": "KOR",
    "Korea": "KOR",
    "Čína": "CHN",
    "Nizozemsko": "NED",
    "Rumunsko": "ROU",
    "Estonsko": "EST",
    "Ukrajina": "UKR",
    "Chorvatsko": "CRO",
    "Srbsko": "SRB",
    # EN názvy (kdybys někde měl v DB angličtinu)
    "Canada": "CAN",
    "United States": "USA",
    "Sweden": "SWE",
    "Finland": "FIN",
    "Russia": "RUS",
    "Czechia": "CZE",
    "Czech Republic": "CZE",
    "Slovakia": "SVK",
    "Switzerland": "SUI",
    "Germany": "GER",
    "Latvia": "LAT",
    "Denmark": "DEN",
    "Norway": "NOR",
    "Austria": "AUT",
    "France": "FRA",
    "Belarus": "BLR",
    "Kazakhstan": "KAZ",
    "Slovenia": "SLO",
    "Italy": "ITA",
    "Poland": "POL",
    "Hungary": "HUN",
    "Great Britain": "GBR",
    "United Kingdom": "GBR",
    "Japan": "JPN",
    "South Korea": "KOR",
    "China": "CHN",
    "Netherlands": "NED",
    "Romania": "ROU",
    "Estonia": "EST",
    "Ukraine": "UKR",
    "Croatia": "CRO",
    "Serbia": "SRB",
}

def flag_from_iso2(iso2: str) -> str:
    if not iso2 or len(iso2) != 2:
        return "🏳️"
    iso2 = iso2.upper()
    return "".join(chr(ord(c) + 127397) for c in iso2)

def flag_from_iso3(iso3: str) -> str:
    iso2 = TOP_HOCKEY_ISO3_TO_ISO2.get((iso3 or "").upper())
    return flag_from_iso2(iso2) if iso2 else "🏳️"

def team_flag(team_name: str) -> str:
    iso3 = TEAM_NAME_TO_ISO3.get(team_name)
    return flag_from_iso3(iso3) if iso3 else "🏳️"

def parse_dt(x: str) -> datetime:
    # Supabase timestamp může přijít s "Z"
    return datetime.fromisoformat(x.replace("Z", "+00:00"))

def nice_time(dt: datetime) -> str:
    # zobraz v lokálním čase prohlížeče (Streamlit to renderuje jako text)
    return dt.astimezone().strftime("%H:%M")


# =====================
# App init
# =====================
load_dotenv()
st.set_page_config(page_title="Zápasy", page_icon="🏒")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# navázání session (RLS)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# Sidebar
with st.sidebar:
    st.markdown("## 🏒 Tipovačka")
    st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
    st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
    st.markdown("---")
    if st.button("🚪 Odhlásit se"):
        st.session_state.clear()
        st.switch_page("app.py")

# Guard
user = st.session_state.get("user")
if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

user_id = user["id"]

st.title("🏒 Zápasy")

# =====================
# 1) Načti zápasy
# =====================
matches_res = (
    supabase.table("matches")
    .select("id, home_team, away_team, starts_at")
    .order("starts_at")
    .execute()
)
matches = matches_res.data or []
if not matches:
    st.info("V databázi nejsou žádné zápasy.")
    st.stop()

# =====================
# 2) Načti moje tipy
# =====================
pred_res = (
    supabase.table("predictions")
    .select("match_id, home_score, away_score, scorer_player_id")
    .eq("user_id", user_id)
    .execute()
)
preds = pred_res.data or []
pred_by_match = {p["match_id"]: p for p in preds}

# =====================
# 3) Přednačti hráče pro všechny týmy v jednom dotazu
# =====================
teams = sorted({m["home_team"] for m in matches} | {m["away_team"] for m in matches})

players_res = (
    supabase.table("players")
    .select("*")  # tolerantní – vezme i club_name/country3 pokud existují
    .in_("team_name", teams)
    .execute()
)
all_players = players_res.data or []

players_by_team = {}
for p in all_players:
    players_by_team.setdefault(p.get("team_name"), []).append(p)

def player_row_label(p: dict) -> str:
    name = p.get("full_name", "").strip()
    club = (p.get("club_name") or p.get("club") or p.get("club_team") or "").strip()
    code3 = (p.get("country3") or p.get("league_code") or p.get("country_code3") or "").strip().upper()

    # vlajka "země kde hraje" (podle kódu u klubu/ligy)
    club_flag = flag_from_iso3(code3) if code3 else "🏳️"

    if club:
        return f"{name} — {club} {club_flag}"
    return f"{name} {club_flag}"

def split_by_role(players: list[dict]) -> tuple[list[dict], list[dict]]:
    atts = [p for p in players if (p.get("role") or "").upper() == "ATT"]
    defs = [p for p in players if (p.get("role") or "").upper() == "DEF"]
    # stabilní řazení
    atts.sort(key=lambda x: (x.get("full_name") or "").lower())
    defs.sort(key=lambda x: (x.get("full_name") or "").lower())
    return atts, defs

def render_team_picker(team_name: str, team_players: list[dict], match_id: str, side: str):
    # side jen pro unikátní klíče (home/away)
    flag = team_flag(team_name)

    st.markdown(f'<div class="picker-title">{flag} {team_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="picker-subtitle">Klikni na hráče (vybereš jen 1 pro celý zápas).</div>', unsafe_allow_html=True)

    atts, defs = split_by_role(team_players)

    # Útočníci
    st.markdown('<div class="picker-section">Útočníci</div>', unsafe_allow_html=True)
    if not atts:
        st.caption("— žádní útočníci v databázi —")
    else:
        for p in atts:
            pid = p.get("id")
            if not pid:
                continue
            key = f"pick_{match_id}_{side}_{pid}"
            if st.button(player_row_label(p), key=key):
                st.session_state[f"scorer_{match_id}"] = pid

    # mezera
    st.markdown('<div class="picker-gap"></div>', unsafe_allow_html=True)

    # Obránci
    st.markdown('<div class="picker-section">Obránci</div>', unsafe_allow_html=True)
    if not defs:
        st.caption("— žádní obránci v databázi —")
    else:
        for p in defs:
            pid = p.get("id")
            if not pid:
                continue
            key = f"pick_{match_id}_{side}_{pid}"
            if st.button(player_row_label(p), key=key):
                st.session_state[f"scorer_{match_id}"] = pid

# =====================
# 4) UI zápasů
# =====================
now = datetime.now(timezone.utc)

for m in matches:
    match_id = m["id"]
    home = m["home_team"]
    away = m["away_team"]
    starts_at = parse_dt(m["starts_at"])
    starts_txt = nice_time(starts_at)

    pred = pred_by_match.get(match_id) or {}
    default_home = int(pred.get("home_score") or 0)
    default_away = int(pred.get("away_score") or 0)
    default_scorer = pred.get("scorer_player_id")

    # inicializace session selection pro match
    state_key = f"scorer_{match_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = default_scorer

    with st.expander(f"{home} vs {away}", expanded=False):
        st.caption(f"Začátek: {starts_txt}")

        # skóre
        c1, c2 = st.columns(2)
        with c1:
            home_score = st.number_input(f"{home} (góly)", min_value=0, max_value=99, value=default_home, key=f"hs_{match_id}")
        with c2:
            away_score = st.number_input(f"{away} (góly)", min_value=0, max_value=99, value=default_away, key=f"as_{match_id}")

        st.markdown("---")

        # výběr střelce ve 2 sloupcích
        st.subheader("⚽ Vybrat střelce (1 hráč)")

        home_players = players_by_team.get(home, [])
        away_players = players_by_team.get(away, [])

        left, right = st.columns(2, gap="large")
        with left:
            render_team_picker(home, home_players, match_id, "home")
        with right:
            render_team_picker(away, away_players, match_id, "away")

        st.markdown("---")

        # clear
        if st.button("— nevybírat střelce —", key=f"clear_{match_id}", type="secondary"):
            st.session_state[state_key] = None

        chosen_player_id = st.session_state.get(state_key)

        # zobraz vybraného střelce pod tipem jako: vlajka nároďáku + jméno
        if chosen_player_id:
            chosen_player = next((p for p in all_players if p.get("id") == chosen_player_id), None)
            if chosen_player:
                nat_flag = team_flag(chosen_player.get("team_name"))
                st.info(f"Vybraný střelec: {nat_flag} {chosen_player.get('full_name')}")
        else:
            st.warning("Chybí tip na střelce.")

        # uložit tip
        if st.button("💾 Uložit tip", key=f"save_{match_id}", type="primary"):
            payload = {
                "user_id": user_id,
                "match_id": match_id,
                "home_score": int(home_score),
                "away_score": int(away_score),
                "scorer_player_id": chosen_player_id,
            }

            try:
                supabase.table("predictions").upsert(
                    payload,
                    on_conflict="user_id,match_id",
                ).execute()
                st.success("Tip uložen ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Uložení selhalo: {e}")