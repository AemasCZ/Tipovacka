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
# Guard: musí být přihlášený
# =====================
user = st.session_state.get("user")
if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

# Pokud máš RLS, bez tokenů to může padat
if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

user_id = user["id"]

# =====================
# Ověření admina přes profiles.is_admin
# =====================
try:
    prof = (
        supabase.table("profiles")
        .select("email, is_admin")
        .eq("id", user_id)
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
st.caption("Sem nahráváš/zakládáš soupisky. Nikde veřejně se nezobrazují – hráči se ukážou jen při výběru střelce u zápasu.")

team_name = st.text_input("Název týmu (musí přesně sedět s matches.home_team / matches.away_team)")

uploaded = st.file_uploader("Nahraj obrázek soupisky (pro kontrolu)", type=["png", "jpg", "jpeg", "webp"])
if uploaded:
    st.image(uploaded, use_container_width=True)

st.markdown("### Vlož text ze soupisky")
st.caption("Zatím nepoužíváme OCR automaticky (kvůli spolehlivosti). Nejrychlejší je zkopírovat text z webu/zdroje a vložit sem.")
raw_text = st.text_area(
    "Text ve formátu jako: Defenders: ... Forwards: ... (Name (Team, CODE), ...)",
    height=220,
)

# Mapování 3-letter kódů na roli vlajky (ISO2 pro emoji vlajky)
# (emoji vlajku v DB nepotřebujeme ukládat – jen ji ty chceš v textovém výpisu)
COUNTRY_3_TO_2 = {
    "ITA": "IT",
    "GER": "DE",
    "CZE": "CZ",
    "SUI": "CH",
    "SLO": "SI",
}

def parse_players(text: str):
    """
    Vytáhne hráče z textu ve formátu:
    Defenders: Name (Team, CODE), Name (Team, CODE).
    Forwards: ...
    Vrací list dictů: {full_name, team_name, role}
    """
    if not text:
        return []

    # normalizace whitespace
    t = " ".join(text.replace("\n", " ").split())

    out = []

    # vysekneme sekce defenders/forwards (nevadí když jedna chybí)
    def_section = ""
    fwd_section = ""

    m_def = re.search(r"Defenders:\s*(.*?)(?:Forwards:|$)", t, flags=re.IGNORECASE)
    if m_def:
        def_section = m_def.group(1).strip()

    m_fwd = re.search(r"Forwards:\s*(.*)$", t, flags=re.IGNORECASE)
    if m_fwd:
        fwd_section = m_fwd.group(1).strip()

    # pattern: Name (Team, CODE)
    pattern = re.compile(r"([^()]+?)\s*\(([^,]+?),\s*([A-Z]{3})\)")

    def add_section(section_text: str, role: str):
        if not section_text:
            return
        for name, team, code3 in pattern.findall(section_text):
            full_name = name.strip().rstrip(",")
            team_raw = team.strip()
            # role je ATT / DEF do DB
            out.append(
                {
                    "full_name": full_name,
                    "team_name": team_raw,
                    "role": role,
                    "country3": code3.strip().upper(),
                }
            )

    add_section(def_section, "DEF")
    add_section(fwd_section, "ATT")

    return out

def flag_from_country3(code3: str) -> str:
    iso2 = COUNTRY_3_TO_2.get(code3)
    if not iso2:
        return "🏳️"
    # převod ISO2 -> emoji vlajka
    return "".join(chr(ord(c) + 127397) for c in iso2)

if st.button("🔎 Parse & náhled", type="secondary"):
    if not raw_text.strip():
        st.error("Vlož text.")
    else:
        parsed = parse_players(raw_text)
        if not parsed:
            st.error("Nepodařilo se nic naparsovat. Zkontroluj formát textu.")
        else:
            st.success(f"Nalezeno hráčů: {len(parsed)}")
            st.markdown("#### Náhled (tak jak to chceš ty)")
            # tisk pro tebe: Jméno (Tým 🇨🇿)
            for p in parsed:
                fl = flag_from_country3(p["country3"])
                st.write(f"- {p['full_name']} ({p['team_name']} {fl}) — {('Útočník' if p['role']=='ATT' else 'Obránce')}")

            st.session_state["parsed_players_cache"] = parsed

st.markdown("---")

if st.button("💾 Uložit do databáze", type="primary"):
    if not team_name.strip():
        st.error("Vyplň team_name (musí sedět s názvem týmu v matches).")
        st.stop()

    parsed = st.session_state.get("parsed_players_cache")
    if not parsed:
        # fallback: když uživatel rovnou klikne bez náhledu
        parsed = parse_players(raw_text)

    if not parsed:
        st.error("Nemám co uložit (nejdřív vlož text a dej Parse & náhled).")
        st.stop()

    # Pozor: v textu může být tým různý (protože hráči hrají v různých klubech)
    # Ty ale chceš soupisku pro konkrétní tým => přepíšeme team_name na hodnotu z inputu
    payload = []
    for p in parsed:
        payload.append(
            {
                "team_name": team_name.strip(),
                "full_name": p["full_name"],
                "role": p["role"],
                "source": "upload_text",
                "created_by": user_id,
            }
        )

    try:
        # (volitelně) smažeme starou soupisku toho týmu a vložíme novou
        supabase.table("players").delete().eq("team_name", team_name.strip()).execute()

        # vložíme novou
        supabase.table("players").insert(payload).execute()

        st.success(f"Uloženo ✅ Soupiska týmu '{team_name.strip()}' byla přepsána ({len(payload)} hráčů).")
        st.session_state.pop("parsed_players_cache", None)
    except Exception as e:
        st.error(f"Uložení selhalo: {e}")