import os
from datetime import datetime, timezone, date

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# =====================
# CSS – schová default Streamlit navigaci + header
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
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
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env")
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
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

user_id = user["id"]

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# =====================
# UI
# =====================
st.title("🏒 Zápasy")

def parse_dt(x: str):
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        return None

now = datetime.now(timezone.utc)
today = now.date()

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
# 2) Načti moje tipy (predictions)
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
# 3) Rozdělení zápasů podle dne
# =====================
by_day = {}
teams_set = set()

for m in matches:
    dt = parse_dt(m["starts_at"])
    if not dt:
        continue
    m["_dt"] = dt
    d = dt.date()
    by_day.setdefault(d, []).append(m)

    # nasbíráme týmy pro jednorázové načtení soupisek
    teams_set.add(m["home_team"])
    teams_set.add(m["away_team"])

days_sorted = sorted(by_day.keys())
future_days = [d for d in days_sorted if d >= today]
past_days = [d for d in days_sorted if d < today]

def day_label(d: date):
    return d.strftime("%d.%m.%Y")

# =====================
# 4) Jednorázově načti VŠECHNY hráče pro všechny týmy
#    (největší zrychlení: konec N+1 dotazů)
# =====================
players_by_team = {t: [] for t in teams_set}

if teams_set:
    players_res = (
        supabase.table("players")
        .select("id, team_name, full_name, role")
        .in_("team_name", list(teams_set))
        .execute()
    )
    players = players_res.data or []

    for p in players:
        t = p.get("team_name")
        if t in players_by_team:
            players_by_team[t].append(p)

    # seřazení: ATT první, DEF druhý, pak jméno
    def sort_key(p):
        role_order = 0 if p.get("role") == "ATT" else 1
        return (role_order, p.get("full_name", ""))

    for t in players_by_team:
        players_by_team[t] = sorted(players_by_team[t], key=sort_key)

# =====================
# Render jednoho zápasu
# =====================
def match_row(m: dict):
    match_id = m["id"]
    dt = m["_dt"]
    time_str = dt.strftime("%H:%M")

    title = f"{m['home_team']} vs {m['away_team']}"
    has_tip = match_id in pred_by_match

    if has_tip:
        p = pred_by_match[match_id]
        status = f"✅ Natipováno ({p['home_score']} : {p['away_score']})"
    else:
        status = "⏳ Chybí tip"

    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"### {title}")
        st.caption(f"Začátek: {time_str}")
        st.write(status)

    with right:
        if dt > now:
            # FORM = obrovské zrychlení UX (nererunuje se na každé kliknutí v inputu)
            with st.form(key=f"form_{match_id}"):
                default_home = pred_by_match.get(match_id, {}).get("home_score", 0)
                default_away = pred_by_match.get(match_id, {}).get("away_score", 0)

                home_score = st.number_input(
                    f"{m['home_team']} (góly)",
                    min_value=0,
                    max_value=30,
                    value=int(default_home),
                    key=f"h_{match_id}",
                )
                away_score = st.number_input(
                    f"{m['away_team']} (góly)",
                    min_value=0,
                    max_value=30,
                    value=int(default_away),
                    key=f"a_{match_id}",
                )

                # --- výběr střelce z obou týmů (1 hráč) ---
                home_team = m["home_team"]
                away_team = m["away_team"]

                home_players = players_by_team.get(home_team, [])
                away_players = players_by_team.get(away_team, [])
                combined = home_players + away_players

                options = [("— nevybírat —", None)]
                for p in combined:
                    role_label = "Útočník" if p["role"] == "ATT" else "Obránce"
                    label = f"{p['team_name']} — {p['full_name']} ({role_label})"
                    options.append((label, p["id"]))

                saved_scorer_id = pred_by_match.get(match_id, {}).get("scorer_player_id")
                default_index = 0
                if saved_scorer_id:
                    for i, (_, pid) in enumerate(options):
                        if pid == saved_scorer_id:
                            default_index = i
                            break

                with st.expander("⚽ Vybrat střelce (1 hráč)", expanded=False):
                    if len(options) == 1:
                        st.info("Pro tento zápas zatím není nahraná soupiska v tabulce players.")
                        chosen_player_id = None
                    else:
                        chosen_label = st.radio(
                            "Vyber jednoho hráče z obou týmů:",
                            options=[o[0] for o in options],
                            index=default_index,
                            key=f"sc_{match_id}",
                        )
                        chosen_player_id = None
                        for lbl, pid in options:
                            if lbl == chosen_label:
                                chosen_player_id = pid
                                break

                submitted = st.form_submit_button("Uložit tip")
                if submitted:
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
        else:
            st.info("Zápas už začal / proběhl – tip nelze měnit.")

    st.divider()

# =====================
# Sekce: Nadcházející
# =====================
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

# =====================
# Sekce: Odehrané
# =====================
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