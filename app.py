# app.py
import os
import time
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

from ui_layout import apply_o2_style, render_hero, card

load_dotenv()

st.set_page_config(page_title="Tipovačka", page_icon="🏒", layout="wide")
apply_o2_style()

# ---------------------
# Supabase
# ---------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Pokud už máš tokeny, navážeme session (kvůli RLS)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    try:
        supabase.auth.set_session(
            st.session_state["access_token"],
            st.session_state["refresh_token"],
        )
    except Exception:
        # tokeny můžou být expirované -> necháme UI, uživatel se přihlásí znovu
        pass


# ---------------------
# Helpers
# ---------------------
def set_logged_in_session(auth_response):
    """
    auth_response: výsledek supabase.auth.sign_in_with_password(...)
    """
    # supabase-py vrací objekt s .session a .user (podle verze)
    sess = getattr(auth_response, "session", None) or auth_response.get("session")
    usr = getattr(auth_response, "user", None) or auth_response.get("user")

    if not sess or not usr:
        raise Exception("Chybí session/user v auth response.")

    st.session_state["access_token"] = sess.access_token
    st.session_state["refresh_token"] = sess.refresh_token
    st.session_state["user"] = {"id": usr.id, "email": usr.email}

    # Navázat session do supabase klienta
    supabase.auth.set_session(sess.access_token, sess.refresh_token)


def try_ensure_profile_row(user_id: str, email: str):
    """
    Pokusí se vytvořit/upsert profil.
    Pokud máš v DB trigger, který profily zakládá automaticky,
    tohle projde nebo se v klidu chytí exception.
    """
    try:
        supabase.table("profiles").upsert(
            {"user_id": user_id, "email": email},
            on_conflict="user_id",
        ).execute()
    except Exception:
        # Nechceme blokovat login kvůli RLS / triggerům
        pass


def cooldown_ok(key: str, seconds: int = 10) -> bool:
    """
    Jednoduchá ochrana proti vícenásobnému submitu během rerunů:
    - uloží timestamp posledního submitu do session_state
    """
    now = time.time()
    last = st.session_state.get(key, 0.0)
    if now - last < seconds:
        return False
    st.session_state[key] = now
    return True


# ---------------------
# HERO
# ---------------------
logo_path = "assets/milano_cortina.png"  # <- sem dej logo (png)

render_hero(
    "Tipovačka",
    "Milano Cortina 2026 • tipuj výsledky, střelce a umístění.",
    image_path=logo_path,
)

# Pokud je user přihlášený, můžeš rovnou nabídnout navigaci
user = st.session_state.get("user")
if user:
    with card("✅ Jsi přihlášený", f"{user.get('email', '')}"):
        col1, col2, col3 = st.columns([1, 1, 1], gap="large")
        with col1:
            if st.button("🏒 Jít na Zápasy", type="primary", use_container_width=True):
                st.switch_page("pages/2_Zapasy.py")
        with col2:
            if st.button("🏆 Jít na Leaderboard", type="secondary", use_container_width=True):
                st.switch_page("pages/3_Leaderboard.py")
        with col3:
            if st.button("🚪 Odhlásit", type="secondary", use_container_width=True):
                # vyčistit session
                for k in ["access_token", "refresh_token", "user"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    st.stop()


# ---------------------
# AUTH UI (tabs)
# ---------------------
tab_login, tab_register = st.tabs(["Přihlášení", "Registrace"])

# ================
# LOGIN
# ================
with tab_login:
    with card("🔐 Přihlášení", "Zadej email a heslo"):
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="např. jiri@o2.cz")
            password = st.text_input("Heslo", type="password")
            submitted = st.form_submit_button("Přihlásit se")

        if submitted:
            if not cooldown_ok("login_submit_ts", seconds=3):
                st.warning("Počkej chvilku a zkus to znovu.")
                st.stop()

            if not email or not password:
                st.error("Vyplň email i heslo.")
            else:
                try:
                    auth = supabase.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    set_logged_in_session(auth)
                    try_ensure_profile_row(st.session_state["user"]["id"], st.session_state["user"]["email"])
                    st.success("✅ Přihlášeno.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Chyba při přihlášení: {e}")


# ================
# REGISTER
# ================
with tab_register:
    with card("🆕 Registrace", "Po registraci se může vyžadovat potvrzení emailu."):
        with st.form("register_form", clear_on_submit=False):
            reg_email = st.text_input("Email", placeholder="např. miloslav.tlapa@o2.cz")
            reg_password = st.text_input("Heslo", type="password")
            reg_password2 = st.text_input("Potvrzení hesla", type="password")
            submitted_reg = st.form_submit_button("Zaregistrovat se")

        if submitted_reg:
            # cooldown delší -> ať se nevyčerpá email rate limit
            if not cooldown_ok("register_submit_ts", seconds=15):
                st.warning("Registrace už byla odeslaná – počkej 15s a zkus to znovu.")
                st.stop()

            if not reg_email or not reg_password or not reg_password2:
                st.error("Vyplň email a obě hesla.")
            elif reg_password != reg_password2:
                st.error("Hesla se neshodují.")
            elif len(reg_password) < 6:
                st.error("Heslo musí mít alespoň 6 znaků.")
            else:
                try:
                    # Pozn.: Supabase může posílat potvrzovací email -> to je to, co naráží na rate limit
                    supabase.auth.sign_up(
                        {"email": reg_email.strip(), "password": reg_password}
                    )
                    st.success("✅ Registrace odeslána. Zkontroluj email (potvrzení/aktivace).")
                    st.info("Pokud potvrzovací email nepřijde hned, počkej chvíli a neklikej opakovaně.")
                except Exception as e:
                    # tady nejčastěji bude: "email rate limit exceeded"
                    st.error(f"Chyba při registraci: {e}")