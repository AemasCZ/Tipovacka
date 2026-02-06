import os
from datetime import datetime, timezone, date

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# =====================
# CSS – schová default Streamlit navigaci + header + drobný vzhled
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }

        /* Hezčí expander */
        div[data-testid="stExpander"] details {
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.02);
            padding: 6px 10px;
        }

        /* Buttony v gridu ať jsou přes celou šířku */
        div[data-testid="column"] button[kind="secondary"]{
            width: 100%;
            white-space: pre-wrap;
            line-height: 1.2;
        }

        /* Trochu menší mezery mezi prvky */
        .block-container { padding-top: 1.2rem; }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Zápasy", page_icon="🏒")

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
# Sidebar – vlastní menu
# =====================
with st.sidebar:
    st.markdown("## 🏒 Tipovačka")
    st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
    st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
    st.markdown("---")

    if st.button("🚪 Odhlásit se"):
        st.session_state.clear()
        st.switch_page("app.py")

# =====================
# Guard: musí být přihlášený
# =====================
user = st.session_state.get("user")
if not user:
    st.warning("Nejsi přihlášený. Jdi do Login.")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

user_id = user["id"]

# =====================
# Pomocné funkce
# =====================
def parse_dt(x: str):
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None

def iso2_flag(iso2: str) -> str:
    if not iso2 or len(iso2) != 2:
        return "🏳️"
    iso2 = iso2.upper()
    return "".join(chr(ord(c) + 127397) for c in iso2)

def chunks(lst, n=3):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def safe_get(d: dict, key: str, default=None):
    try:
        return d.get(key, default)
    except Exception:
        return default

# =====================
# Vlajky – top 30 (aliasy)
# =====================
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

# 3-letter -> ISO2 (vlajka země klubu/ligy u hráče)
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

# =====================
# Čas
# =====================
now = datetime.now(timezone.utc)
today = now.date()

def day_label(d: date):
    return d.strftime("%d.%m.%Y")

# =====================
# DB načítání
# =====================
# 1) zápasy
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

# 2) moje tipy (fallback: když nejsou scorer_* sloupce)
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

# 3) rozdělení zápasů podle dne
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

# =====================
# Hráči (cache)
# =====================
@st.cache_data(ttl=120)
def load_players_for_team(team_name: str):
    """
    Očekávané sloupce v players:
      team_name, full_name, role (ATT/DEF)
    Bonus:
      id, club_name, country3
    """
    # nejdřív zkus “full” select
    try:
        res = (
            supabase.table("players")
            .select("id, team_name, full_name, role, club_name, country3")
            .eq("team_name", team_name)
            .order("role")
            .order("full_name")
            .execute()
        )
        return res.data or []
    except Exception:
        # fallback
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

# =====================
# Uložení tipu (upsert) + fallback bez scorer_* sloupců
# =====================
def upsert_prediction(match_id: str, home_score: int, away_score: int, scorer_payload: dict | None = None):
    base_payload = {
        "user_id": user_id,
        "match_id": match_id,
        "home_score": int(home_score),
        "away_score": int(away_score),
    }

    # 1) zkus s “scorer” poli
    if scorer_payload:
        payload = {**base_payload, **scorer_payload}
        try:
            supabase.table("predictions").upsert(payload, on_conflict="user_id,match_id").execute()
            return
        except Exception:
            # 2) fallback: uložit alespoň skóre
            supabase.table("predictions").upsert(base_payload, on_conflict="user_id,match_id").execute()
            return

    # bez střelce
    supabase.table("predictions").upsert(base_payload, on_conflict="user_id,match_id").execute()

# =====================
# UI blok – hráči (po 3 v řádku) + klik = auto-save
# =====================
def render_team_players(team_name: str, match_id: str, side: str):
    players = load_players_for_team(team_name)
    atts = [p for p in players if safe_get(p, "role") == "ATT"]
    defs = [p for p in players if safe_get(p, "role") == "DEF"]

    st.markdown(f"### {team_flag(team_name)} {team_name}")

    def render_group(title: str, group_players: list[dict], role_label: str):
        st.markdown(f"**{title}**")
        if not group_players:
            st.caption("— žádní hráči v DB —")
            return

        for row in chunks(group_players, 3):
            cols = st.columns(3)
            for col, p in zip(cols, row):
                full_name = safe_get(p, "full_name", "Neznámý hráč")
                club = safe_get(p, "club_name", "")
                c3 = safe_get(p, "country3", "")
                club_flag = club_country_flag(c3) if c3 else "🏳️"

                # Text na tlačítku: Jméno + Klub + vlajka země, kde hraje
                label = f"{full_name}\n{club} {club_flag}".strip()

                # stabilní id hráče (pokud nemáš v DB id)
                player_id = safe_get(p, "id") or f"{team_name}:{full_name}:{role_label}"

                if col.button(
                    label,
                    key=f"pick_{match_id}_{side}_{player_id}",
                    type="secondary",
                ):
                    # vezmeme aktuální skóre z inputů
                    h_key = f"h_{match_id}"
                    a_key = f"a_{match_id}"

                    current_home = int(st.session_state.get(h_key, pred_by_match.get(match_id, {}).get("home_score", 0) or 0))
                    current_away = int(st.session_state.get(a_key, pred_by_match.get(match_id, {}).get("away_score", 0) or 0))

                    scorer_payload = {
                        "scorer_player_id": str(player_id),
                        "scorer_name": full_name,
                        "scorer_flag": team_flag(team_name),  # vlajka země za kterou hraje (tým v match)
                        "scorer_team": team_name,
                    }

                    try:
                        upsert_prediction(match_id, current_home, current_away, scorer_payload=scorer_payload)
                        st.success(f"Střelec uložen ✅ {scorer_payload['scorer_flag']} {full_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Uložení střelce selhalo: {e}")

    render_group("Útočníci", atts, "ATT")
    st.write("")  # mezera
    render_group("Obránci", defs, "DEF")

# =====================
# Řádek zápasu
# =====================
def match_row(m: dict):
    match_id = m["id"]
    dt = m["_dt"]
    time_str = dt.strftime("%H:%M")
    title = f"{m['home_team']} vs {m['away_team']}"

    p = pred_by_match.get(match_id, {})
    has_tip = bool(p)

    status = f"✅ Natipováno ({p.get('home_score', 0)} : {p.get('away_score', 0)})" if has_tip else "⏳ Chybí tip"

    left, right = st.columns([3, 2], vertical_alignment="top")

    with left:
        st.markdown(f"### {title}")
        st.caption(f"Začátek: {time_str}")
        st.write(status)

        # vybraný střelec – zobraz pod tipem
        scorer_name = p.get("scorer_name")
        scorer_flag = p.get("scorer_flag")
        if scorer_name:
            st.markdown(f"**Střelec:** {scorer_flag or '🏳️'} {scorer_name}")

    with right:
        if dt > now:
            default_home = int(p.get("home_score", 0) or 0)
            default_away = int(p.get("away_score", 0) or 0)

            home_score = st.number_input(
                f"{m['home_team']} (góly)",
                min_value=0,
                max_value=30,
                value=default_home,
                key=f"h_{match_id}",
            )
            away_score = st.number_input(
                f"{m['away_team']} (góly)",
                min_value=0,
                max_value=30,
                value=default_away,
                key=f"a_{match_id}",
            )

            if st.button("Uložit tip", key=f"save_{match_id}"):
                try:
                    # zachovej střelce, pokud už existuje
                    scorer_payload = None
                    if p.get("scorer_name"):
                        scorer_payload = {
                            "scorer_player_id": p.get("scorer_player_id"),
                            "scorer_name": p.get("scorer_name"),
                            "scorer_flag": p.get("scorer_flag"),
                            "scorer_team": p.get("scorer_team"),
                        }

                    upsert_prediction(match_id, int(home_score), int(away_score), scorer_payload=scorer_payload)
                    st.success("Tip uložen ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Uložení selhalo: {e}")

            with st.expander("⚽ Vybrat střelce (1 hráč) — klik = uložit", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    render_team_players(m["home_team"], match_id, side="home")
                with c2:
                    render_team_players(m["away_team"], match_id, side="away")
        else:
            st.info("Zápas už začal / proběhl – tip nelze měnit.")

    st.divider()

# =====================
# UI
# =====================
st.title("🏒 Zápasy")

st.subheader("📅 Nadcházející zápasy")
if not future_days:
    st.info("Žádné nadcházející dny.")
else:
    for d in future_days:
        ms = by_day[d]
        total = len(ms)
        done = sum(1 for mm in ms if mm["id"] in pred_by_match)

        with st.expander(f"{day_label(d)}  •  Natipováno {done}/{total}", expanded=False):
            for mm in ms:
                match_row(mm)

st.subheader("🕘 Odehrané")
if not past_days:
    st.info("Zatím nic odehraného.")
else:
    for d in reversed(past_days):
        ms = by_day[d]
        total = len(ms)
        done = sum(1 for mm in ms if mm["id"] in pred_by_match)

        with st.expander(f"{day_label(d)}  •  Natipováno {done}/{total}", expanded=False):
            for mm in ms:
                match_row(mm)