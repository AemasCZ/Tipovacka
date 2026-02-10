import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

# Základní nastavení
load_dotenv()
st.set_page_config(page_title="Admin – Manuální body", page_icon="✏️", layout="wide")

# Supabase připojení
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Session nastavení pro RLS (Row Level Security - zabezpečení na úrovni řádků)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

# Aplikuj styly
apply_o2_style()

# Uživatel a menu
user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

# Hero sekce
render_hero(
    "Admin – Manuální body",
    "Přidej nebo odeber body uživatelům ručně. Body se připočítají k celkovému skóre.",
    image_path="assets/olymp.png",
)

# Kontrola přihlášení
if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
        st.stop()

# Kontrola admin práv
try:
    prof = supabase.table("profiles").select("user_id, is_admin").eq("user_id", user["id"]).single().execute()
    if not (prof.data or {}).get("is_admin"):
        st.error("Tato stránka je jen pro admina.")
        st.stop()
except Exception as e:
    st.error(f"Nelze ověřit admina: {e}")
    st.stop()

# Načti uživatele z databáze
try:
    profiles = (supabase.table("profiles").select("user_id, email, points").execute().data or [])
except Exception as e:
    st.error(f"Nelze načíst uživatele: {e}")
    st.stop()

# UI pro přidávání bodů
with card("✏️ Přidej/odeber body"):
    if not profiles:
        st.info("Nejsou žádní uživatelé.")
    else:
        # Dropdown s uživateli
        user_options = [f"{p['email']} (aktuálně: {p.get('points', 0)} bodů)" for p in profiles]
        selected_idx = st.selectbox("Vyber uživatele", range(len(profiles)), format_func=lambda i: user_options[i])
        
        selected_user = profiles[selected_idx]
        
        # Input pro body
        points_to_add = st.number_input("Body k přidání/odebrání", value=0, step=1, 
                                       help="Kladné číslo přidá body, záporné odebere")
        reason = st.text_input("Důvod (volitelné)", placeholder="např. bonus za aktivitu")
        
        # Tlačítko pro uložení
        if st.button("💾 Uložit změnu", type="primary", disabled=(points_to_add == 0)):
            try:
                current_points = int(selected_user.get("points", 0))
                new_points = max(0, current_points + int(points_to_add))  # Nesmí klesnout pod 0
                
                # Aktualizace v databázi
                supabase.table("profiles").update(
                    {"points": new_points}
                ).eq("user_id", selected_user["user_id"]).execute()
                
                action = "přidáno" if points_to_add > 0 else "odebráno"
                st.success(f"✅ Bodů {action}: {abs(points_to_add)} → {selected_user['email']} má nyní {new_points} bodů")
                
                if reason:
                    st.info(f"Důvod: {reason}")
                
                # Obnovení stránky pro aktuální data
                st.rerun()
                
            except Exception as e:
                st.error(f"Chyba při ukládání: {e}")
                st.code(str(e))  # Pro debugging

# Přehled všech uživatelů
with card("👥 Přehled všech uživatelů"):
    if profiles:
        # Seřazení podle bodů (nejvíce bodů nahoře)
        sorted_profiles = sorted(profiles, key=lambda x: -int(x.get("points", 0)))
        
        # Zobrazení tabulky
        table_data = []
        for i, p in enumerate(sorted_profiles, 1):
            medal = ""
            if i == 1: medal = "🥇"
            elif i == 2: medal = "🥈"  
            elif i == 3: medal = "🥉"
            
            table_data.append({
                "#": f"{i} {medal}",
                "Email": p["email"], 
                "Body": int(p.get("points", 0))
            })
        
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info("Žádní uživatelé.")