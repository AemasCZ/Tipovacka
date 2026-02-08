# ui_layout.py
import base64
from pathlib import Path
import streamlit as st


def _img_to_base64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def apply_o2_style():
    st.markdown(
        """
        <style>
          /* =========================================================
             1) ODSTRANĚNÍ STREAMLIT SIDEBARU (černý pruh vlevo)
             ========================================================= */
          section[data-testid="stSidebar"] { display: none !important; }
          div[data-testid="collapsedControl"] { display: none !important; }
          [data-testid="stSidebarNav"] { display:none !important; }

          /* Header pryč */
          header[data-testid="stHeader"] { display:none !important; }

          /* App background */
          html, body, [data-testid="stAppViewContainer"]{
            background: #f6f8fc !important;
            color: #0b1220 !important;
          }

          /* Streamlit někdy drží odsazení kvůli sidebaru */
          [data-testid="stAppViewContainer"] .main { margin-left: 0 !important; }

          .block-container{
            padding-top: 1.1rem !important;
            max-width: 1200px !important;
          }

          :root{
            --bg: #f6f8fc;
            --card: #ffffff;
            --text: #0b1220;
            --muted: rgba(11,18,32,.65);
            --border: rgba(11,18,32,.12);
            --shadow: 0 10px 28px rgba(11,18,32,.10);
            --blue: #1b4cff;
            --blue2:#0e2aa8;
            --radius: 18px;
          }

          /* =========================================================
             2) BUTTON FIX (dlaždice + hráči jako střelci)
             ========================================================= */
          .stButton > button{
            border-radius: 999px !important;
            font-weight: 800 !important;
            transition: all .15s ease !important;
          }

          .stButton > button[kind="primary"]{
            background: var(--blue) !important;
            color: #fff !important;
            border: 0 !important;
            box-shadow: var(--shadow) !important;
          }
          .stButton > button[kind="primary"]:hover{
            filter: brightness(1.05) !important;
            transform: translateY(-1px);
          }

          .stButton > button[kind="secondary"]{
            background: #fff !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            box-shadow: 0 6px 16px rgba(11,18,32,.08) !important;
          }
          .stButton > button[kind="secondary"]:hover{
            border-color: rgba(27,76,255,.35) !important;
            box-shadow: 0 10px 24px rgba(11,18,32,.12) !important;
            transform: translateY(-1px);
          }

          .stButton > button:disabled{
            opacity: .55 !important;
            cursor: not-allowed !important;
            transform: none !important;
          }

          /* =========================================================
             3) INPUTS FIX (Email/Heslo byly tmavé)
             ========================================================= */
          /* wrapper */
          [data-baseweb="input"] > div{
            background: #fff !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: 0 6px 16px rgba(11,18,32,.06) !important;
          }

          /* input text */
          [data-baseweb="input"] input{
            color: var(--text) !important;
            font-weight: 600 !important;
          }

          /* placeholder */
          [data-baseweb="input"] input::placeholder{
            color: rgba(11,18,32,.45) !important;
            font-weight: 600 !important;
          }

          /* focus (modrá linka) */
          [data-baseweb="input"] > div:focus-within{
            border-color: rgba(27,76,255,.55) !important;
            box-shadow: 0 0 0 4px rgba(27,76,255,.14) !important;
          }

          /* eye icon / input buttons */
          [data-baseweb="input"] button{
            color: rgba(11,18,32,.55) !important;
          }

          /* =========================================================
             4) TABS FIX (Přihlášení / Registrace nejsou vidět)
             ========================================================= */
          div[data-testid="stTabs"]{
            margin-top: 6px;
          }

          /* tab list bar */
          div[data-testid="stTabs"] [data-baseweb="tab-list"]{
            gap: 10px !important;
            border-bottom: 1px solid rgba(11,18,32,.10) !important;
            padding-bottom: 6px !important;
          }

          /* each tab button */
          div[data-testid="stTabs"] [data-baseweb="tab"]{
            background: transparent !important;
            border-radius: 999px !important;
            padding: 10px 14px !important;
            font-weight: 900 !important;
            font-size: 15px !important;
            color: rgba(11,18,32,.55) !important;
            transition: all .12s ease !important;
          }

          /* selected tab */
          div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"]{
            color: var(--blue) !important;
          }

          /* selected underline */
          div[data-testid="stTabs"] [data-baseweb="tab-highlight"]{
            background: var(--blue) !important;
            height: 3px !important;
            border-radius: 999px !important;
          }

          /* hover tab */
          div[data-testid="stTabs"] [data-baseweb="tab"]:hover{
            color: rgba(11,18,32,.85) !important;
            background: rgba(255,255,255,.65) !important;
            border: 1px solid rgba(11,18,32,.08) !important;
          }

          /* =========================================================
             5) CARD STYL
             ========================================================= */
          .o2-card{
            background: var(--card);
            border: 1px solid rgba(11,18,32,.10);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 16px 16px 10px 16px;
            margin: 12px 0 16px 0;
          }
          .o2-card-title{
            font-size: 18px;
            font-weight: 900;
            margin: 0 0 6px 0;
          }
          .o2-muted{
            color: var(--muted);
            font-size: 13px;
          }

          /* =========================================================
             6) HERO STYL
             ========================================================= */
          .o2-hero{
            border-radius: 28px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.35);
            box-shadow: 0 18px 50px rgba(11,18,32,.18);
            background: linear-gradient(135deg, var(--blue2), var(--blue));
            padding: 34px 34px;
            min-height: 220px;
            margin-bottom: 16px;
          }
          .o2-hero-grid{
            display:flex;
            gap: 18px;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
          }
          .o2-hero h1{
            margin:0;
            font-size: 44px;
            line-height: 1.05;
            color: #fff;
            font-weight: 950;
            letter-spacing: -0.02em;
          }
          .o2-hero p{
            margin:10px 0 0 0;
            color: rgba(255,255,255,.88);
            font-size: 15px;
            max-width: 650px;
          }
          .o2-hero-img{
            width: 380px;
            max-width: 42vw;
            height: 220px;
            border-radius: 22px;
            background-size: cover;
            background-position: center;
            box-shadow: 0 18px 50px rgba(0,0,0,.25);
          }

          /* =========================================================
             7) TOPBAR
             ========================================================= */
          .o2-topbar{
            background: rgba(255,255,255,.78);
            border: 1px solid rgba(11,18,32,.08);
            border-radius: 999px;
            box-shadow: 0 10px 28px rgba(11,18,32,.08);
            padding: 8px 10px;
            margin-bottom: 12px;
            position: sticky;
            top: 10px;
            z-index: 999;
            backdrop-filter: blur(10px);
          }

          [data-testid="stAlert"]{
            border-radius: 16px;
          }

          @media (max-width: 980px){
            .o2-hero h1{ font-size: 34px; }
            .o2-hero-img{ width: 100%; max-width: 100%; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, image_path: str | None = None):
    img_style = ""
    if image_path:
        b64 = _img_to_base64(image_path)
        if b64:
            img_style = f"background-image:url('data:image/png;base64,{b64}');"

    st.markdown(
        f"""
        <div class="o2-hero">
          <div class="o2-hero-grid">
            <div style="min-width:320px;flex:1">
              <h1>{title}</h1>
              <p>{subtitle}</p>
            </div>
            <div class="o2-hero-img" style="{img_style}"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(title: str, subtitle: str | None = None):
    st.markdown('<div class="o2-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="o2-card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="o2-muted">{subtitle}</div>', unsafe_allow_html=True)
    return _CardCtx()


class _CardCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        st.markdown("</div>", unsafe_allow_html=True)