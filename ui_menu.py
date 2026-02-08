# ui_menu.py
import streamlit as st


def render_top_menu(user: dict | None, supabase=None, user_id: str | None = None, active: str | None = None):
    """
    O2-like top menu. Nepoužívá sidebar.
    active: název aktivní stránky (pro info), nemusí být.
    """
    st.markdown('<div class="o2-topbar">', unsafe_allow_html=True)

    c0, c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1, 1, 1.2], vertical_alignment="center")

    with c0:
        st.markdown("### 🏒 Tipovačka")

    with c1:
        if st.button("🏒 Zápasy", use_container_width=True, type="secondary"):
            st.switch_page("pages/2_Zapasy.py")

    with c2:
        if st.button("🏅 Umístění", use_container_width=True, type="secondary"):
            st.switch_page("pages/6_Umisteni.py")

    with c3:
        if st.button("🏆 Leaderboard", use_container_width=True, type="secondary"):
            st.switch_page("pages/3_Leaderboard.py")

    with c4:
        # Admin tlačítko jen pokud je session flag is_admin
        is_admin = bool(st.session_state.get("is_admin", False))
        if is_admin:
            if st.button("🛠️ Admin", use_container_width=True, type="secondary"):
                st.switch_page("pages/4_Admin_Vyhodnoceni.py")
        else:
            st.button("🛠️ Admin", use_container_width=True, type="secondary", disabled=True)

    with c5:
        if user:
            email = user.get("email") or "Přihlášen"
            st.caption(f"👤 {email}")

            if st.button("Odhlásit", use_container_width=True, type="primary"):
                try:
                    if supabase is not None:
                        supabase.auth.sign_out()
                except Exception:
                    pass
                st.session_state.clear()
                st.switch_page("app.py")
        else:
            if st.button("🔐 Login", use_container_width=True, type="primary"):
                st.switch_page("app.py")

    st.markdown("</div>", unsafe_allow_html=True)