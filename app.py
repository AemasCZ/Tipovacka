# app.py
import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()

st.set_page_config(page_title="Tipovačka", page_icon="🏒", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
APP_BASE_URL = os.getenv("APP_BASE_URL")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Obnovení session
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

user = st.session_state.get("user")

# ---------- Helper: query params ----------
def get_query_param(name: str):
    try:
        val = st.query_params.get(name)
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        params = st.experimental_get_query_params()
        vals = params.get(name)
        return vals[0] if vals else None

# ---------- Helper: profil ----------
def load_profile(user_id: str, email: str):
    """
    profiles: user_id (uuid), email (text), points (int), is_admin (bool)
    """
    try:
        res = (
            supabase.table("profiles")
            .select("user_id, email, points, is_admin")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        try:
            supabase.table("profiles").insert(
                {"user_id": user_id, "email": email, "points": 0, "is_admin": False}
            ).execute()
            res2 = (
                supabase.table("profiles")
                .select("user_id, email, points, is_admin")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return res2.data
        except Exception:
            return None

# Po loginu: načti profil + admin flag do session
if user and not st.session_state.get("profile_loaded"):
    prof = load_profile(user["id"], user.get("email", ""))
    st.session_state["profile"] = prof
    st.session_state["is_admin"] = bool((prof or {}).get("is_admin", False))
    st.session_state["profile_loaded"] = True

apply_o2_style()
render_top_menu(user, supabase=supabase, user_id=(user["id"] if user else None))

render_hero(
    "Tipovačka",
    "Milano Cortina 2026 • tipuj výsledky, střelce a umístění. Vše v O2-like stylu.",
    image_path="assets/olymp.png",  # když neexistuje, hero se ukáže bez obrázku
)

# Už přihlášen
if user:
    with card("✅ Přihlášen"):
        st.success(f"Přihlášen jako **{user.get('email','—')}**")
        if bool(st.session_state.get("is_admin", False)):
            st.info("Jsi přihlášen jako **admin** ✅")
        st.info("Použij menu nahoře (Zápasy / Umístění / Leaderboard).")
        st.stop()

# Email verifikace
if get_query_param("verified") == "1":
    st.success("Email byl úspěšně potvrzen ✅ Přihlaš se níže.")

tab_login, tab_signup = st.tabs(["Přihlášení", "Registrace"])

with tab_login:
    with card("🔐 Přihlášení", "Zadej email a heslo"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Heslo", type="password", key="login_pw")

        if st.button("Přihlásit se", type="primary"):
            if not email or not password:
                st.error("Vyplň email i heslo.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state["user"] = res.user.model_dump()
                    st.session_state["access_token"] = res.session.access_token
                    st.session_state["refresh_token"] = res.session.refresh_token
                    st.session_state.pop("profile_loaded", None)
                    st.success("Přihlášení úspěšné ✅")
                    st.switch_page("pages/2_Zapasy.py")
                except Exception:
                    st.error("Přihlášení se nepovedlo – zkontroluj email a heslo.")

with tab_signup:
    with card("🆕 Registrace", "Po registraci se může vyžadovat potvrzení emailu."):
        new_email = st.text_input("Email", key="signup_email")
        new_pw = st.text_input("Heslo", type="password", key="signup_pw")
        new_pw2 = st.text_input("Heslo znovu", type="password", key="signup_pw2")

        if st.button("Zaregistrovat se", type="primary"):
            if not new_email or not new_pw or not new_pw2:
                st.error("Vyplň email a obě hesla.")
            elif new_pw != new_pw2:
                st.error("Hesla se neshodují.")
            elif len(new_pw) < 6:
                st.error("Heslo musí mít alespoň 6 znaků.")
            else:
                try:
                    signup_payload = {"email": new_email, "password": new_pw}
                    if APP_BASE_URL:
                        signup_payload["options"] = {"emailRedirectTo": f"{APP_BASE_URL}/?verified=1"}
                    supabase.auth.sign_up(signup_payload)
                    st.success("Registrace proběhla ✅ Teď se přihlas.")
                except Exception:
                    st.error("Registrace se nepovedla. Zkus jiný email nebo později.")