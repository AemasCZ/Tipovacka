import streamlit as st


def _resolve_is_admin(supabase=None, user_id=None) -> bool:
    if "is_admin" in st.session_state:
        return bool(st.session_state.get("is_admin", False))

    if supabase and user_id:
        try:
            prof = (
                supabase.table("profiles")
                .select("is_admin")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            is_admin = bool((prof.data or {}).get("is_admin", False))
            st.session_state["is_admin"] = is_admin
            return is_admin
        except Exception:
            return False

    return False


def render_top_menu(user=None, *, supabase=None, user_id=None, show_admin: bool = True):
    st.markdown(
        """
        <style>
            div[data-testid="collapsedControl"] { display: none; }
            .top-menu-sticky {
                position: sticky;
                top: 0;
                z-index: 1000;
                background: var(--background-color);
                padding-top: 0.25rem;
                padding-bottom: 0.25rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='top-menu-sticky'>", unsafe_allow_html=True)
    with st.expander("▾ Menu", expanded=False):
        if user:
            st.page_link("pages/2_Zapasy.py", label="🏒 Zápasy")
            st.page_link("pages/3_Leaderboard.py", label="🏆 Leaderboard")

            if show_admin and _resolve_is_admin(supabase, user_id):
                st.page_link("pages/1_Soupisky_Admin.py", label="🛠 Admin")

            st.markdown("---")
            if st.button("🚪 Odhlásit se", key="top_menu_logout"):
                st.session_state.clear()
                st.switch_page("app.py")
        else:
            st.markdown("🔐 Přihlas se pro menu")
    st.markdown("</div>", unsafe_allow_html=True)
