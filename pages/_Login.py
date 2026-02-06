import os
import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

# =========================
# Init
# =========================
load_dotenv()

st.set_page_config(page_title="Přihlášení", page_icon="🔐")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

st.title("🔐 Přihlášení")

# =========================
# Už přihlášen
# =========================
if "user" in st.session_state:
    st.success(f"Přihlášen jako {st.session_state['user']['email']}")

    if st.button("Odhlásit"):
        st.session_state.clear()
        st.rerun()

    st.stop()

# =========================
# Login form
# =========================
with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Heslo", type="password")
    submit = st.form_submit_button("Přihlásit se")

if submit:
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

        st.session_state["user"] = {
            "id": res.user.id,
            "email": res.user.email,
        }
        st.session_state["access_token"] = res.session.access_token
        st.session_state["refresh_token"] = res.session.refresh_token

        st.success("Přihlášení OK ✅")
        st.rerun()

    except Exception as e:
        st.error(f"Nepodařilo se přihlásit: {e}")
