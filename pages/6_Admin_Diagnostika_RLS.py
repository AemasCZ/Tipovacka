# pages/6_Admin_Diagnostika_RLS.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Diagnostika RLS (Admin)", page_icon="🔍", layout="wide")

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

# ✅ Navázání session
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
# UI
# =====================
st.title("🔍 Diagnostika RLS")
st.caption("Tento skript ti ukáže, co přesně vidí aktuálně přihlášený uživatel kvůli RLS policies.")

# =====================
# Test 1: Profily
# =====================
st.markdown("---")
st.subheader("1️⃣ Test: Tabulka `profiles`")

try:
    prof_res = supabase.table("profiles").select("user_id, email, points, is_admin").execute()
    profiles = prof_res.data or []
    
    st.success(f"✅ Vidím {len(profiles)} profilů")
    st.dataframe(profiles, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"❌ Chyba při čtení profiles: {e}")
    st.code(str(e))

# =====================
# Test 2: Predictions
# =====================
st.markdown("---")
st.subheader("2️⃣ Test: Tabulka `predictions`")

try:
    preds_res = supabase.table("predictions").select(
        "user_id, match_id, home_score, away_score, points_awarded, scorer_name"
    ).execute()
    preds = preds_res.data or []
    
    st.success(f"✅ Vidím {len(preds)} tipů (predictions)")
    
    # Seskupení podle user_id
    by_user = {}
    for p in preds:
        uid = p.get("user_id")
        if uid not in by_user:
            by_user[uid] = []
        by_user[uid].append(p)
    
    st.write(f"**Rozložení podle uživatelů:**")
    for uid, tips in by_user.items():
        # Najdi email
        email = "neznámý"
        for prof in profiles:
            if prof.get("user_id") == uid:
                email = prof.get("email", uid)
                break
        
        total_pts = sum(int(t.get("points_awarded") or 0) for t in tips)
        st.write(f"- **{email}**: {len(tips)} tipů, celkem {total_pts} bodů")
    
    st.markdown("**Detaily všech tipů:**")
    st.dataframe(preds, use_container_width=True, hide_index=True)
    
except Exception as e:
    st.error(f"❌ Chyba při čtení predictions: {e}")
    st.code(str(e))
    st.warning(
        "⚠️ **PROBLÉM DETEKOVÁN!** Pokud vidíš tuto chybu, znamená to, že RLS "
        "neumožňuje číst predictions jiných uživatelů. To je důvod, proč leaderboard "
        "neukazuje body nikoho kromě tebe."
    )

# =====================
# Test 3: Matches
# =====================
st.markdown("---")
st.subheader("3️⃣ Test: Tabulka `matches`")

try:
    matches_res = supabase.table("matches").select(
        "id, home_team, away_team, starts_at, final_home_score, final_away_score"
    ).execute()
    matches = matches_res.data or []
    
    st.success(f"✅ Vidím {len(matches)} zápasů")
    st.dataframe(matches, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"❌ Chyba při čtení matches: {e}")
    st.code(str(e))

# =====================
# Test 4: Scorer Results
# =====================
st.markdown("---")
st.subheader("4️⃣ Test: Tabulka `scorer_results`")

try:
    scorer_res = supabase.table("scorer_results").select(
        "match_id, scorer_player_id, scorer_name, scorer_team, did_score"
    ).execute()
    scorers = scorer_res.data or []
    
    st.success(f"✅ Vidím {len(scorers)} záznamů střelců")
    if scorers:
        st.dataframe(scorers, use_container_width=True, hide_index=True)
    else:
        st.info("Zatím žádné záznamy střelců.")
except Exception as e:
    st.error(f"❌ Chyba při čtení scorer_results: {e}")
    st.code(str(e))

# =====================
# Shrnutí
# =====================
st.markdown("---")
st.subheader("📋 Shrnutí")

st.markdown("""
### Co by mělo fungovat:

1. **Profiles** - Měl bys vidět **všechny profily** (ne jen svůj)
2. **Predictions** - Měl bys vidět **všechny tipy všech uživatelů** (ne jen svoje)
3. **Matches** - Měl bys vidět **všechny zápasy**
4. **Scorer Results** - Měl bys vidět **všechny výsledky střelců**

### Pokud něco nefunguje:

- Otevři **Supabase Dashboard** → **SQL Editor**
- Spusť SQL script `quick_fix_rls.sql`, který jsem vytvořil
- Alternativně spusť kompletní `fix_rls_policies.sql`

### Důvod problému:

RLS (Row Level Security) policies v Supabase omezují, co můžeš číst.
Pokud policies říkají "můžeš vidět jen svoje tipy", leaderboard nemůže
sečíst body ostatních uživatelů. Proto všichni mají 0 bodů.
""")
