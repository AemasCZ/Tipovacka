import streamlit as st


def _safe_is_admin(supabase, user_id: str | None) -> bool:
    """
    Zkusíme zjistit admin flag:
    1) pokud už je v session_state, použijeme ho
    2) jinak zkusíme načíst z profiles
    """
    if st.session_state.get("is_admin") is True:
        return True
    if not supabase or not user_id:
        return False

    try:
        res = (
            supabase.table("profiles")
            .select("is_admin")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return bool((res.data or {}).get("is_admin", False))
    except Exception:
        return False


def _logout(supabase=None):
    """
    Odhlášení:
    - zkusíme supabase.auth.sign_out()
    - vyčistíme session_state
    """
    try:
        if supabase:
            supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.clear()
    st.rerun()


def render_top_menu(user: dict | None, supabase=None, user_id: str | None = None):
    """
    Top menu (mobil-friendly):
    - tlačítka nahoře v řádku
    - admin sekce pod tím (expander), jen když je admin

    Použití:
      render_top_menu(user, supabase=supabase, user_id=user_id)
    """

    # ----- CSS -----
    st.markdown(
        """
        <style>
          .tg-topbar {
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            border-radius: 16px;
            padding: 12px 12px;
            margin: 8px 0 16px 0;
          }
          .tg-user {
            opacity: 0.85;
            font-size: 13px;
            margin: 0 0 10px 0;
          }
          .tg-small {
            opacity: 0.75;
            font-size: 12px;
          }
          /* tlačítka v topbaru hezky na výšku */
          .tg-topbar button {
            white-space: nowrap;
          }
          /* trochu zmenšit padding tlačítek (mobil) */
          div[data-testid="stButton"] > button {
            padding: 0.45rem 0.65rem;
            border-radius: 12px;
          }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ----- TOP BAR WRAP -----
    st.markdown('<div class="tg-topbar">', unsafe_allow_html=True)

    # uživatel info
    if user and user.get("email"):
        st.markdown(f'<div class="tg-user">👤 Přihlášen jako <b>{user["email"]}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="tg-user">👤 Nepřihlášen</div>', unsafe_allow_html=True)

    # ----- hlavní navigace (tlačítka) -----
    # 3 hlavní stránky + logout
    c1, c2, c3, c4 = st.columns([1, 1, 1, 0.9], vertical_alignment="center")

    with c1:
        if st.button("🏒 Zápasy", use_container_width=True, key="nav_zapasy"):
            st.switch_page("pages/2_Zapasy.py")

    with c2:
        if st.button("🏅 Umístění", use_container_width=True, key="nav_umisteni"):
            st.switch_page("pages/6_Umisteni.py")

    with c3:
        if st.button("🏆 Leaderboard", use_container_width=True, key="nav_leaderboard"):
            st.switch_page("pages/3_Leaderboard.py")

    with c4:
        if user and st.button("🚪 Odhlásit", use_container_width=True, key="nav_logout"):
            _logout(supabase)

    # ----- admin sekce -----
    is_admin = _safe_is_admin(supabase, user_id)

    if is_admin:
        with st.expander("🛠️ Admin", expanded=False):
            st.caption("Admin nástroje")

            a1, a2, a3 = st.columns(3, vertical_alignment="center")
            with a1:
                if st.button("🧾 Soupisky", use_container_width=True, key="admin_soupisky"):
                    st.switch_page("pages/1_Soupisky_Admin.py")
            with a2:
                if st.button("🧮 Vyhodnocení zápasů", use_container_width=True, key="admin_vyhod_zapasy"):
                    st.switch_page("pages/4_Admin_Vyhodnoceni.py")
            with a3:
                if st.button("🧮 Vyhodnocení umístění", use_container_width=True, key="admin_vyhod_umisteni"):
                    st.switch_page("pages/7_Admin_Umisteni.py")

            b1, b2 = st.columns(2, vertical_alignment="center")
            with b1:
                if st.button("🔄 Synchronizace bodů", use_container_width=True, key="admin_sync_points"):
                    st.switch_page("pages/5_Admin_Sync_Points.py")
            with b2:
                if st.button("🔍 Diagnostika RLS", use_container_width=True, key="admin_diag_rls"):
                    st.switch_page("pages/6_Admin_Diagnostika_RLS.py")

            st.markdown('<div class="tg-small">Tip: Pokud admin stránky nejdou, je to RLS (policies).</div>',
                        unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)