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
st.markdown(
    """
    <style>
        /* skryje horní lištu (kde se někdy zobrazuje název stránky) */
        header[data-testid="stHeader"] {
            display: none;
        }

        /* skryje default multipage navigaci (app/Login/Zapasy/Leaderboard) */
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# SUPABASE
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env")
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
# ZJIŠTĚNÍ ADMINA (jen pokud je přihlášený)
# =====================
is_admin = False
if user:
    try:
        prof = (
            supabase.table("profiles")
            .select("is_admin")
            .eq("id", user["id"])
            .single()
            .execute()
        )
        is_admin = bool((prof.data or {}).get("is_admin"))
    except Exception:
        is_admin = False

# =====================
# SIDEBAR – VLASTNÍ MENU
# =====================
with st.sidebar:
    st.markdown("## 🏒 Tipovačka")

    if user:
        st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
        st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")
        st.markdown("---")

        if st.button("🚪 Odhlásit se"):
            st.session_state.clear()
            st.rerun()

        # ---- ADMIN sekce úplně dole ----
        if is_admin:
            st.markdown("---")
            st.page_link("pages/1_Soupisky_Admin.py", label="ADMIN sekce")
    else:
        st.markdown("🔐 Přihlaš se nebo se registruj")
        # ---- ADMIN sekce úplně dole (viditelná jen adminovi => bez loginu ji neschováme, ale admin stejně není známý) ----
        # Necháváme schované, protože bez přihlášení nevíme, kdo je admin.

# =====================
# OBSAH STRÁNKY
# =====================
if user:
    st.success(f"Přihlášen jako **{user['email']}**")
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