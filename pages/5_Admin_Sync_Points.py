# pages/5_Admin_Sync_Points.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Synchronizace bodů (Admin)", page_icon="🔄", layout="wide")

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

        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
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
# UI
# =====================
st.title("🔄 Synchronizace bodů (Admin)")
st.caption("Tento skript přepočítá celkové body v profiles.points na základě součtu predictions.points_awarded pro každého uživatele.")

# =====================
# Načtení dat
# =====================
try:
    prof_res = (
        supabase.table("profiles")
        .select("user_id, email, points")
        .execute()
    )
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profily: {e}")
    st.stop()

try:
    preds_res = (
        supabase.table("predictions")
        .select("user_id, points_awarded")
        .execute()
    )
    preds = preds_res.data or []
except Exception as e:
    st.error(f"Nelze načíst tipy: {e}")
    st.stop()

# Spočítáme správné body ze predictions
points_by_user = {}
for p in preds:
    uid = p.get("user_id")
    if not uid:
        continue
    awarded = p.get("points_awarded")
    if awarded is None:
        awarded = 0
    points_by_user[uid] = points_by_user.get(uid, 0) + int(awarded)

# Porovnáme s profiles.points
comparison = []
needs_sync = False

for p in profiles:
    uid = p.get("user_id")
    email = p.get("email") or uid
    current_pts = int(p.get("points") or 0)
    correct_pts = int(points_by_user.get(uid, 0))
    diff = correct_pts - current_pts
    
    if diff != 0:
        needs_sync = True
    
    comparison.append({
        "Uživatel": email,
        "Aktuální body (profiles.points)": current_pts,
        "Správné body (Σ predictions.points_awarded)": correct_pts,
        "Rozdíl": diff,
        "Status": "✅ OK" if diff == 0 else f"⚠️ Opravit ({diff:+d})"
    })

st.markdown("### 📊 Porovnání bodů")
st.dataframe(comparison, use_container_width=True, hide_index=True)

if not needs_sync:
    st.success("✅ Všechny body jsou synchronizované! Není třeba nic dělat.")
else:
    st.warning("⚠️ Nalezeny nesrovnalosti v bodech. Doporučuji spustit synchronizaci.")
    
    st.markdown("---")
    st.subheader("🔄 Synchronizace")
    st.markdown("Po kliknutí na tlačítko níže se všechny hodnoty v `profiles.points` přepíší na správné součty z `predictions.points_awarded`.")
    
    if st.button("🔄 Synchronizovat body", type="primary"):
        try:
            updated = 0
            errors = []
            
            for p in profiles:
                uid = p.get("user_id")
                correct_pts = int(points_by_user.get(uid, 0))
                current_pts = int(p.get("points") or 0)
                
                if correct_pts != current_pts:
                    try:
                        supabase.table("profiles").update(
                            {"points": correct_pts}
                        ).eq("user_id", uid).execute()
                        updated += 1
                    except Exception as e:
                        errors.append(f"{p.get('email', uid)}: {e}")
            
            if errors:
                st.error(f"Některé aktualizace selhaly:\n" + "\n".join(errors))
            else:
                st.success(f"✅ Synchronizace dokončena! Aktualizováno {updated} uživatelů.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Chyba při synchronizaci: {e}")
