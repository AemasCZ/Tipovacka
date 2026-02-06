# pages/1_Soupisky_Admin.py
import os
import re
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
st.set_page_config(page_title="Soupisky (Admin)", page_icon="🧾")

# =====================
# Supabase klient
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
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
if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

user_id = user["id"]

# =====================
# ✅ Ověření admina přes profiles.is_admin
# =====================
try:
    prof = (
        supabase.table("profiles")
        .select("email, is_admin")
        .eq("user_id", user_id)
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
# UI
# =====================
st.title("🧾 Soupisky (Admin)")
st.caption(
    "Sem nahráváš/zakládáš soupisky. Hráči se ukážou při výběru střelce u zápasu. "
    "Teď ukládáme i klub + zemi (+ volitelně ligu)."
)

team_name = st.text_input("Název týmu (musí přesně sedět s matches.home_team / matches.away_team)")

uploaded = st.file_uploader("Nahraj obrázek soupisky (pro kontrolu)", type=["png", "jpg", "jpeg", "webp"])
if uploaded:
    st.image(uploaded, use_container_width=True)

st.markdown("### Vlož text ze soupisky")
st.caption(
    "Formát podporujeme takhle (flexibilně):\n"
    "- Defenders: Name (Club, USA), Name (Club, CAN) ... Forwards: ...\n"
    "- nebo i: Name (Club, NHL, USA)  /  Name (Club, USA, NHL)\n"
)

raw_text = st.text_area(
    "Text",
    height=220,
)

# =====================
# Helper – vlajka z country3 (v admin náhledu)
# =====================
COUNTRY3_TO_ISO2 = {
    "CAN": "CA", "USA": "US", "SWE": "SE", "FIN": "FI", "CZE": "CZ", "SVK": "SK", "RUS": "RU",
    "SUI": "CH", "GER": "DE", "LAT": "LV", "DEN": "DK", "NOR": "NO", "AUT": "AT", "FRA": "FR",
    "BLR": "BY", "KAZ": "KZ", "SLO": "SI", "ITA": "IT", "JPN": "JP", "KOR": "KR", "CHN": "CN",
    "GBR": "GB", "HUN": "HU", "POL": "PL", "UKR": "UA", "NED": "NL", "EST": "EE", "ROU": "RO",
    "CRO": "HR", "LTU": "LT",
}

def iso2_flag(iso2: str | None) -> str:
    if not iso2 or len(iso2) != 2:
        return "🏳️"
    iso2 = iso2.upper()
    return "".join(chr(ord(c) + 127397) for c in iso2)

def flag_from_country3(code3: str | None) -> str:
    if not code3:
        return "🏳️"
    iso2 = COUNTRY3_TO_ISO2.get(code3.upper())
    return iso2_flag(iso2) if iso2 else "🏳️"

def clean_name(x: str) -> str:
    # řeší: ", Adrian Kempe" atd.
    if not x:
        return ""
    return x.strip().lstrip(",").strip()

# =====================
# Parsování – vytáhne full_name, role, club_name, country3, league_name, league_country3
# =====================
def parse_player_item(item: str):
    """
    item např:
      "Adrian Kempe (Buffalo Sabres, USA)"
      "Adrian Kempe (Buffalo Sabres, NHL, USA)"
      "Adrian Kempe (Buffalo Sabres, USA, NHL)"
    """
    item = item.strip()
    if not item:
        return None

    # rozsekání: "Name ( ... )"
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", item)
    if not m:
        return None

    name = clean_name(m.group(1))
    inside = m.group(2)

    parts = [p.strip() for p in inside.split(",") if p.strip()]
    club_name = ""
    country3 = ""
    league_name = ""
    league_country3 = ""

    # heuristika:
    # - club je typicky první položka
    # - country3 je položka přesně 3 písmena (USA/CAN/ITA...) – bereme první nalezenou
    # - zbytek, co není country3 a není club, bereme jako league
    if len(parts) >= 1:
        club_name = parts[0]

    codes = [p for p in parts if re.fullmatch(r"[A-Z]{3}", p)]
    if codes:
        country3 = codes[0]

    # league: první "non-club non-country" položka
    rest = []
    for p in parts[1:]:
        if re.fullmatch(r"[A-Z]{3}", p):
            continue
        rest.append(p)

    if rest:
        league_name = rest[0]

    # pokud máš i league_country3 separátně (někdo to může posílat), vezmeme druhý kód
    if len(codes) >= 2:
        league_country3 = codes[1]
    else:
        league_country3 = country3  # fallback: aspoň něco

    return {
        "full_name": name,
        "club_name": club_name,
        "country3": (country3 or "").upper(),
        "league_name": league_name,
        "league_country3": (league_country3 or "").upper(),
    }

def parse_players(text: str):
    if not text:
        return []

    t = " ".join(text.replace("\n", " ").split())

    def_section = ""
    fwd_section = ""

    m_def = re.search(r"Defenders:\s*(.*?)(?:Forwards:|$)", t, flags=re.IGNORECASE)
    if m_def:
        def_section = m_def.group(1).strip()

    m_fwd = re.search(r"Forwards:\s*(.*)$", t, flags=re.IGNORECASE)
    if m_fwd:
        fwd_section = m_fwd.group(1).strip()

    def split_items(section_text: str):
        # rozdělení podle "),", ale zachovat poslední ")"
        # fallback: klasicky podle "),"
        if not section_text:
            return []
        raw = section_text
        raw = raw.replace("),", ")|")
        items = [x.strip().strip(",") for x in raw.split("|") if x.strip()]
        return items

    out = []

    def add_section(section_text: str, role: str):
        for item in split_items(section_text):
            parsed = parse_player_item(item)
            if not parsed:
                continue
            out.append(
                {
                    "full_name": parsed["full_name"],
                    "role": role,
                    "club_name": parsed["club_name"],
                    "country3": parsed["country3"],
                    "league_name": parsed["league_name"],
                    "league_country3": parsed["league_country3"],
                }
            )

    add_section(def_section, "DEF")
    add_section(fwd_section, "ATT")
    return out

# =====================
# Akce
# =====================
if st.button("🔎 Parse & náhled", type="secondary"):
    if not raw_text.strip():
        st.error("Vlož text.")
    else:
        parsed = parse_players(raw_text)
        if not parsed:
            st.error("Nepodařilo se nic naparsovat. Zkontroluj formát textu.")
        else:
            st.success(f"Nalezeno hráčů: {len(parsed)}")
            st.markdown("#### Náhled")
            for p in parsed:
                fl = flag_from_country3(p.get("country3"))
                club = p.get("club_name") or "—"
                lg = p.get("league_name") or ""
                lg_part = f", {lg}" if lg else ""
                st.write(
                    f"- {p['full_name']} ({club}{lg_part}, {fl}) — "
                    f"{('Útočník' if p['role']=='ATT' else 'Obránce')}"
                )
            st.session_state["parsed_players_cache"] = parsed

st.markdown("---")

if st.button("💾 Uložit do databáze", type="primary"):
    if not team_name.strip():
        st.error("Vyplň team_name (musí sedět s názvem týmu v matches).")
        st.stop()

    parsed = st.session_state.get("parsed_players_cache") or parse_players(raw_text)
    if not parsed:
        st.error("Nemám co uložit (nejdřív vlož text a dej Parse & náhled).")
        st.stop()

    payload = []
    for p in parsed:
        payload.append(
            {
                "team_name": team_name.strip(),          # národní tým (pro párování s matches)
                "full_name": clean_name(p["full_name"]),
                "role": p["role"],

                # ✅ NOVĚ: klub + země + liga
                "club_name": p.get("club_name") or None,
                "country3": (p.get("country3") or "").upper() or None,
                "league_name": p.get("league_name") or None,
                "league_country3": (p.get("league_country3") or "").upper() or None,

                "source": "upload_text",
                "created_by": user_id,
            }
        )

    try:
        supabase.table("players").delete().eq("team_name", team_name.strip()).execute()
        supabase.table("players").insert(payload).execute()

        st.success(f"Uloženo ✅ Soupiska týmu '{team_name.strip()}' byla přepsána ({len(payload)} hráčů).")
        st.session_state.pop("parsed_players_cache", None)
    except Exception as e:
        st.error(f"Uložení selhalo: {e}")