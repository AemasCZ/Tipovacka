# pages/1_Soupisky_Admin.py
import os
import re
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Admin – Soupisky", page_icon="🧾", layout="wide")

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
    "Admin – Soupisky",
    "Vlož soupisku textem. Uloží se hráči včetně klubu + země + ligy.",
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

# admin check
try:
    prof = supabase.table("profiles").select("user_id, is_admin").eq("user_id", user["id"]).single().execute()
    if not (prof.data or {}).get("is_admin"):
        st.error("Tato stránka je jen pro admina.")
        st.stop()
except Exception as e:
    st.error(f"Nelze ověřit admina: {e}")
    st.stop()

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
    if not x:
        return ""
    return x.strip().lstrip(",").strip()

def parse_player_item(item: str):
    item = item.strip()
    if not item:
        return None

    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", item)
    if not m:
        return None

    name = clean_name(m.group(1))
    inside = m.group(2)
    parts = [p.strip() for p in inside.split(",") if p.strip()]

    club_name = parts[0] if len(parts) >= 1 else ""
    codes = [p for p in parts if re.fullmatch(r"[A-Z]{3}", p)]
    country3 = codes[0] if codes else ""

    rest = []
    for p in parts[1:]:
        if re.fullmatch(r"[A-Z]{3}", p):
            continue
        rest.append(p)
    league_name = rest[0] if rest else ""

    league_country3 = codes[1] if len(codes) >= 2 else country3

    return {"full_name": name, "club_name": club_name, "country3": (country3 or "").upper(), "league_name": league_name, "league_country3": (league_country3 or "").upper()}

def parse_players(text: str):
    if not text:
        return []
    t = " ".join(text.replace("\n", " ").split())

    def_section, fwd_section = "", ""
    m_def = re.search(r"Defenders:\s*(.*?)(?:Forwards:|$)", t, flags=re.IGNORECASE)
    if m_def:
        def_section = m_def.group(1).strip()

    m_fwd = re.search(r"Forwards:\s*(.*)$", t, flags=re.IGNORECASE)
    if m_fwd:
        fwd_section = m_fwd.group(1).strip()

    def split_items(section_text: str):
        if not section_text:
            return []
        raw = section_text.replace("),", ")|")
        return [x.strip().strip(",") for x in raw.split("|") if x.strip()]

    out = []

    def add_section(section_text: str, role: str):
        for item in split_items(section_text):
            parsed = parse_player_item(item)
            if not parsed:
                continue
            out.append({**parsed, "role": role})

    add_section(def_section, "DEF")
    add_section(fwd_section, "ATT")
    return out

with card("🧾 Vstup"):
    team_name = st.text_input("Název týmu (musí sedět s matches.home_team / matches.away_team)")
    uploaded = st.file_uploader("Nahraj obrázek soupisky (pro kontrolu)", type=["png", "jpg", "jpeg", "webp"])
    if uploaded:
        st.image(uploaded, use_container_width=True)

    raw_text = st.text_area("Text ze soupisky", height=220)

with card("🔎 Náhled"):
    if st.button("Parse & náhled", type="primary", use_container_width=True):
        if not raw_text.strip():
            st.error("Vlož text.")
        else:
            parsed = parse_players(raw_text)
            if not parsed:
                st.error("Nepodařilo se nic naparsovat. Zkontroluj formát.")
            else:
                st.success(f"Nalezeno hráčů: {len(parsed)}")
                for p in parsed:
                    fl = flag_from_country3(p.get("country3"))
                    club = p.get("club_name") or "—"
                    lg = p.get("league_name") or ""
                    lg_part = f", {lg}" if lg else ""
                    st.write(f"- {p['full_name']} ({club}{lg_part}, {fl}) — {('Útočník' if p['role']=='ATT' else 'Obránce')}")
                st.session_state["parsed_players_cache"] = parsed

with card("💾 Uložení do DB"):
    if st.button("Uložit", type="primary", use_container_width=True):
        if not team_name.strip():
            st.error("Vyplň team_name.")
            st.stop()

        parsed = st.session_state.get("parsed_players_cache") or parse_players(raw_text)
        if not parsed:
            st.error("Nemám co uložit (nejdřív Parse & náhled).")
            st.stop()

        payload = []
        for p in parsed:
            payload.append({
                "team_name": team_name.strip(),
                "full_name": clean_name(p["full_name"]),
                "role": p["role"],
                "club_name": p.get("club_name") or None,
                "country3": (p.get("country3") or "").upper() or None,
                "league_name": p.get("league_name") or None,
                "league_country3": (p.get("league_country3") or "").upper() or None,
                "source": "upload_text",
                "created_by": user_id,
            })

        try:
            supabase.table("players").delete().eq("team_name", team_name.strip()).execute()
            supabase.table("players").insert(payload).execute()
            st.success(f"Uloženo ✅ Soupiska '{team_name.strip()}' přepsána ({len(payload)} hráčů).")
            st.session_state.pop("parsed_players_cache", None)
        except Exception as e:
            st.error(f"Uložení selhalo: {e}")