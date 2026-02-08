# app.py
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

from ui_layout import apply_o2_style, render_hero, card

load_dotenv()
st.set_page_config(page_title="Tipovačka", page_icon="🏒", layout="wide")
apply_o2_style()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Pokud už máme tokeny, navážeme session
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# HERO + LOGO (vpravo v okně)
render_hero(
    "Tipovačka",
    "Milano Cortina 2026 • tipuj výsledky, střelce a umístění.",
    image_path="assets/milano_cortina_2026.png",  # ✅ sem dej svůj soubor
)

tab_login, tab_register = st.tabs(["Přihlášení", "Registrace"])

# -------------------------
# PŘIHLÁŠENÍ
# -------------------------
with tab_login:
    with card("🔐 Přihlášení", "Zadej email a heslo"):
        email = st.text_input("Email", placeholder="např. jiri@o2.cz")
        password = st.text_input("Heslo", type="password", placeholder="••••••••")

        if st.button("Přihlásit se", type="primary"):
            if not email or not password:
                st.error("Vyplň email i heslo.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )

                    # session + user
                    session = res.session
                    user = res.user

                    if not session or not user:
                        st.error("Přihlášení se nepovedlo (žádná session).")
                    else:
                        st.session_state["user"] = user.model_dump() if hasattr(user, "model_dump") else dict(user)
                        st.session_state["access_token"] = session.access_token
                        st.session_state["refresh_token"] = session.refresh_token

                        # přesměrování
                        st.success("✅ Přihlášeno.")
                        st.switch_page("pages/2_Zapasy.py")  # uprav, pokud máš jinou stránku jako první
                except Exception as e:
                    st.error(f"Chyba při přihlášení: {e}")

# -------------------------
# REGISTRACE
# -------------------------
with tab_register:
    with card("🆕 Registrace", "Po registraci se může vyžadovat potvrzení emailu."):
        reg_email = st.text_input("Email", placeholder="např. nikca@email.cz", key="reg_email")
        reg_password = st.text_input("Heslo", type="password", placeholder="min. 6 znaků", key="reg_pass")
        reg_password2 = st.text_input("Potvrzení hesla", type="password", placeholder="znovu heslo", key="reg_pass2")

        if st.button("Zaregistrovat se", type="primary"):
            if not reg_email or not reg_password:
                st.error("Vyplň email a heslo.")
            elif reg_password != reg_password2:
                st.error("Hesla se neshodují.")
            elif len(reg_password) < 6:
                st.error("Heslo musí mít alespoň 6 znaků.")
            else:
                try:
                    res = supabase.auth.sign_up(
                        {"email": reg_email.strip(), "password": reg_password}
                    )

                    # Pozn: některé projekty vrací session hned, jiné až po potvrzení emailu
                    if getattr(res, "session", None):
                        session = res.session
                        user = res.user
                        st.session_state["user"] = user.model_dump() if hasattr(user, "model_dump") else dict(user)
                        st.session_state["access_token"] = session.access_token
                        st.session_state["refresh_token"] = session.refresh_token
                        st.success("✅ Registrace hotová, jsi přihlášen.")
                        st.switch_page("pages/2_Zapasy.py")
                    else:
                        st.success("✅ Registrace hotová. Zkontroluj email a případně potvrď registraci, pak se přihlas.")
                except Exception as e:
                    st.error(f"Chyba při registraci: {e}")