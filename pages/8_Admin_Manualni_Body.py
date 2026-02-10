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

# Session nastavení pro RLS
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
    "Přidej nebo odeber body uživatelům ručně. Body se ukládají do manual_points_log a aktualizují profiles.points.",
    image_path="assets/olymp.png",
)

# Kontroly přihlášení
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

# Načti uživatele
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
        
        # Inputy
        points_to_add = st.number_input("Body k přidání/odebrání", value=0, step=1, 
                                       help="Kladné číslo přidá body, záporné odebere")
        reason = st.text_input("Důvod (volitelné)", placeholder="např. bonus za aktivitu")
        
        # Uložení
        if st.button("💾 Uložit změnu", type="primary", disabled=(points_to_add == 0)):
            try:
                current_points = int(selected_user.get("points", 0))
                new_points = max(0, current_points + int(points_to_add))
                
                # 1. Vlož záznam do manual_points_log
                log_entry = {
                    "admin_user_id": user_id,
                    "target_user_id": selected_user["user_id"],
                    "change_amount": int(points_to_add),
                    "old_points": current_points,
                    "new_points": new_points,
                    "reason": reason.strip() if reason.strip() else None
                }
                
                supabase.table("manual_points_log").insert(log_entry).execute()
                
                # 2. Aktualizuj profiles.points
                supabase.table("profiles").update(
                    {"points": new_points}
                ).eq("user_id", selected_user["user_id"]).execute()
                
                action = "přidáno" if points_to_add > 0 else "odebráno"
                st.success(f"✅ Bodů {action}: {abs(points_to_add)} → {selected_user['email']} má nyní {new_points} bodů")
                
                if reason:
                    st.info(f"Důvod: {reason}")
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Chyba při ukládání: {e}")
                st.code(str(e))  # Pro debugging

# Přehled změn
with card("📋 Historie manuálních změn"):
    try:
        # Načti historii s joinem na emaily
        logs = supabase.table("manual_points_log").select(
            "created_at, change_amount, old_points, new_points, reason, admin_user_id, target_user_id"
        ).order("created_at", desc=True).limit(20).execute().data or []
        
        if logs:
            # Získej emaily pro admin_user_id a target_user_id
            user_ids = set()
            for log in logs:
                user_ids.add(log["admin_user_id"])
                user_ids.add(log["target_user_id"])
            
            emails_res = supabase.table("profiles").select("user_id, email").in_("user_id", list(user_ids)).execute().data or []
            emails_map = {p["user_id"]: p["email"] for p in emails_res}
            
            # Zobraz tabulku
            table_data = []
            for log in logs:
                admin_email = emails_map.get(log["admin_user_id"], "—")
                target_email = emails_map.get(log["target_user_id"], "—")
                
                table_data.append({
                    "Datum": log["created_at"][:16] if log["created_at"] else "—",
                    "Admin": admin_email,
                    "Uživatel": target_email,
                    "Změna": f"{log['change_amount']:+d}",
                    "Body": f"{log['old_points']} → {log['new_points']}",
                    "Důvod": log["reason"] or "—"
                })
            
            st.dataframe(table_data, use_container_width=True, hide_index=True)
        else:
            st.caption("Zatím žádné manuální změny.")
    except Exception as e:
        st.error(f"Nelze načíst historii: {e}")

# Přehled všech uživatelů
with card("👥 Aktuální stav bodů"):
    if profiles:
        sorted_profiles = sorted(profiles, key=lambda x: -int(x.get("points", 0)))
        
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