import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# =====================
# ZÁKLADNÍ NASTAVENÍ
# =====================
load_dotenv()

st.set_page_config(
    page_title="Tipovačka",
    page_icon="🏒",
    layout="centered",
)

# =====================
# CSS – SCHOVÁNÍ DEFAULT NAV + HEADERU
# =====================
st.set_page_config(
    page_title="Tipovačka",
    page_icon="🏒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =====================
# SUPABASE
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Obnovení session (pokud už je uložená)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

user = st.session_state.get("user")

# =====================
# Helper: načtení profilu (včetně is_admin)
# =====================
def load_profile(user_id: str, email: str):
    """
    profiles tabulka má sloupce:
    user_id (uuid), email (text), points (int), created_at (timestamptz), is_admin (bool)

    1) zkusí načíst řádek podle user_id
    2) když neexistuje, vytvoří ho (is_admin default false)
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
        # pokud profil neexistuje, zkusíme ho vytvořit
        try:
            supabase.table("profiles").insert(
                {
                    "user_id": user_id,
                    "email": email,
                    "points": 0,
                    "is_admin": False,
                }
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

# pokud je user přihlášený, načti jeho profil a ulož admin flag do session_state
if user and not st.session_state.get("profile_loaded"):
    prof = load_profile(user["id"], user.get("email", ""))
    if prof:
        st.session_state["profile"] = prof
        st.session_state["is_admin"] = bool(prof.get("is_admin", False))
    else:
        st.session_state["profile"] = None
        st.session_state["is_admin"] = False
    st.session_state["profile_loaded"] = True

is_admin = bool(st.session_state.get("is_admin", False))

# =====================
# SIDEBAR – VLASTNÍ MENU
# =====================
with st.sidebar:
    st.markdown("## 🏒 Tipovačka")

    if user:
        st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
        st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")

        # ✅ ADMIN se zobrazí jen adminovi
        if is_admin:
            st.page_link("pages/1_Soupisky_Admin.py", label="🛠 Admin")

        st.markdown("---")

        if st.button("🚪 Odhlásit se"):
            st.session_state.clear()
            st.rerun()
    else:
        st.markdown("🔐 Přihlaš se nebo se registruj")

# =====================
# OBSAH STRÁNKY
# =====================
if user:
    st.success(f"Přihlášen jako **{user['email']}**")
    if is_admin:
        st.info("Jsi přihlášen jako **admin** ✅")
    st.info("Pokračuj přes menu vlevo 👈")
    st.stop()

# ===== LOGIN / REGISTRACE =====
st.title("🔐 Přihlášení")

tab_login, tab_signup = st.tabs(["Přihlášení", "Registrace"])

# ---------------------
# PŘIHLÁŠENÍ
# ---------------------
with tab_login:
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Heslo", type="password", key="login_pw")

    if st.button("Přihlásit se", type="primary"):
        if not email or not password:
            st.error("Vyplň email i heslo.")
        else:
            try:
                res = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )

                st.session_state["user"] = res.user.model_dump()
                st.session_state["access_token"] = res.session.access_token
                st.session_state["refresh_token"] = res.session.refresh_token

                # ✅ po loginu načti profil (včetně is_admin)
                st.session_state.pop("profile_loaded", None)
                st.success("Přihlášení úspěšné ✅")
                st.switch_page("pages/2_Zapasy.py")

            except Exception:
                st.error("Přihlášení se nepovedlo – zkontroluj email a heslo.")

# ---------------------
# REGISTRACE
# ---------------------
with tab_signup:
    new_email = st.text_input("Email", key="signup_email")
    new_pw = st.text_input("Heslo", type="password", key="signup_pw")
    new_pw2 = st.text_input("Heslo znovu", type="password", key="signup_pw2")

    if st.button("Zaregistrovat se"):
        if not new_email or not new_pw or not new_pw2:
            st.error("Vyplň email a obě hesla.")
        elif new_pw != new_pw2:
            st.error("Hesla se neshodují.")
        elif len(new_pw) < 6:
            st.error("Heslo musí mít alespoň 6 znaků.")
        else:
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_pw})
                st.success(
                    "Registrace proběhla ✅ Teď se přihlas."
                    " (Pokud je zapnuté potvrzení emailu, přijde ti email.)"
                )
            except Exception:
                st.error("Registrace se nepovedla. Zkus jiný email nebo později.")