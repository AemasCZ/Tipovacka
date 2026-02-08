# pages/3_Leaderboard.py
import os
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Leaderboard", page_icon="🏆", layout="wide")

# =====================
# CSS (globální)
# =====================
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none; }
        [data-testid="stSidebarNav"] { display: none; }
        .block-container { padding-top: 1.2rem; }

        .card {
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.02);
            border-radius: 16px;
            padding: 16px;
            margin: 10px 0 16px 0;
        }
        .muted { opacity: 0.75; font-size: 14px; }
        button[kind="secondary"], button[kind="primary"] { width: 100% !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# Supabase
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# session (RLS)
if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(
        st.session_state["access_token"],
        st.session_state["refresh_token"],
    )

# =====================
# Guard: musí být přihlášený
# =====================
user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

if not user:
    st.warning("Nejsi přihlášený.")
    if st.button("Jít na přihlášení"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

st.title("🏆 Leaderboard")

# =====================
# admin?
# =====================
is_admin = False
try:
    my_prof = (
        supabase.table("profiles")
        .select("is_admin")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    is_admin = bool((my_prof.data or {}).get("is_admin", False))
except Exception:
    is_admin = False

if is_admin:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🛠️ Admin")
    st.markdown('<div class="muted">Vyhodnocení zápasů a přepočet bodů.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧮 Vyhodnocení zápasů", type="primary"):
            st.switch_page("pages/4_Admin_Vyhodnoceni.py")
    with col2:
        if st.button("🔄 Synchronizace bodů", type="secondary"):
            st.switch_page("pages/5_Admin_Sync_Points.py")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Načtení dat
# =====================
try:
    prof_res = (
        supabase.table("profiles")
        .select("user_id, email")
        .execute()
    )
    profiles = prof_res.data or []
except Exception as e:
    st.error(f"Nelze načíst profily (RLS?): {e}")
    st.stop()

try:
    preds_res = (
        supabase.table("predictions")
        .select("user_id, points_awarded")
        .execute()
    )
    preds = preds_res.data or []
except Exception as e:
    st.error(f"Nelze načíst tipy (RLS?): {e}")
    st.stop()

# =====================
# Spočítáme body pro každého uživatele
# =====================
points_by_user = {}
for p in preds:
    uid = p.get("user_id")
    if not uid:
        continue
    awarded = p.get("points_awarded") or 0
    points_by_user[uid] = points_by_user.get(uid, 0) + int(awarded)

rows = []
for pr in profiles:
    uid = pr.get("user_id")
    rows.append(
        {
            "uid": uid,
            "user": pr.get("email") or uid,
            "points": int(points_by_user.get(uid, 0)),
        }
    )

# ✅ seřazení podle bodů (desc), při shodě podle jména (asc)
rows.sort(key=lambda r: (-r["points"], (r["user"] or "").lower()))

if not rows:
    st.info("Zatím nejsou žádné tipy s body.")
    st.stop()

# =====================
# HTML leaderboard (spolehlivě přes components.html)
# =====================
def esc(x: str) -> str:
    return html_lib.escape(x or "")

html_rows = []
for i, r in enumerate(rows, start=1):
    user_txt = esc(r["user"])
    pts = int(r["points"])

    badge = '<span class="top-badge">TOP</span>' if i == 1 else ""
    you = "you" if r["uid"] == user_id else ""

    html_rows.append(
        f"""
        <tr class="{you}">
            <td class="col-rank">{i}</td>
            <td class="col-user">{user_txt} {badge}</td>
            <td class="col-points">{pts}</td>
        </tr>
        """
    )

# výška komponenty (ať to není useknuté)
row_h = 44
header_h = 44
pad = 24
height = min(700, header_h + len(rows) * row_h + pad)

table_html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
    body {{
        margin: 0;
        padding: 0;
        color: rgba(255,255,255,0.92);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        background: transparent;
    }}

    .lb-wrap {{ margin-top: 8px; }}

    table.lb {{
        width: 100%;
        border-collapse: collapse;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.02);
        border-radius: 14px;
        overflow: hidden;
    }}

    thead th {{
        text-align: left;
        font-weight: 800;
        font-size: 13px;
        opacity: 0.85;
        padding: 12px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.10);
        white-space: nowrap;
    }}

    tbody td {{
        padding: 12px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        font-size: 14px;
        vertical-align: middle;
    }}

    tbody tr:last-child td {{ border-bottom: none; }}

    /* sloupce */
    .col-rank {{ width: 44px; text-align: right; opacity: 0.9; }}
    .col-user {{ width: auto; }}
    .col-points {{ width: 90px; text-align: right; font-weight: 900; }}

    /* TOP badge */
    .top-badge {{
        display: inline-block;
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.14);
        background: rgba(255,255,255,0.04);
        margin-left: 8px;
        opacity: 0.9;
    }}

    /* zvýrazni přihlášeného */
    tr.you {{
        background: rgba(255,255,255,0.04);
    }}
</style>
</head>
<body>
<div class="lb-wrap">
  <table class="lb">
    <thead>
      <tr>
        <th class="col-rank">#</th>
        <th class="col-user">Uživatel</th>
        <th class="col-points">Body</th>
      </tr>
    </thead>
    <tbody>
      {''.join(html_rows)}
    </tbody>
  </table>
</div>
</body>
</html>
"""

components.html(table_html, height=height, scrolling=False)

# =====================
# Debug sekce (volitelně)
# =====================
if is_admin and st.checkbox("🐛 Zobrazit debug info", value=False):
    st.markdown("---")
    st.subheader("Debug: Kontrola synchronizace")

    try:
        prof_points = (
            supabase.table("profiles")
            .select("user_id, email, points")
            .execute()
        )

        debug_rows = []
        for p in prof_points.data or []:
            uid = p.get("user_id")
            email = p.get("email") or uid
            profile_pts = int(p.get("points") or 0)
            calc_pts = int(points_by_user.get(uid, 0))
            diff = profile_pts - calc_pts

            debug_rows.append({
                "Email": email,
                "profiles.points": profile_pts,
                "Σ predictions.points_awarded": calc_pts,
                "Rozdíl": diff
            })

        st.dataframe(debug_rows, use_container_width=True, hide_index=True)

        if any(r["Rozdíl"] != 0 for r in debug_rows):
            st.warning("⚠️ Nalezeny nesrovnalosti! Možná je potřeba synchronizovat body.")
    except Exception as e:
        st.error(f"Chyba při načítání debug info: {e}")