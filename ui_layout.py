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
           1) ZÁKLAD + ODSTRANĚNÍ SIDEBARU / HEADERU
           ========================================================= */
        section[data-testid="stSidebar"] { display: none !important; }
        div[data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebarNav"] { display:none !important; }
        header[data-testid="stHeader"] { display:none !important; }

        html, body, [data-testid="stAppViewContainer"]{
          background: #f6f8fc !important;
          color: #0b1220 !important;
        }

        [data-testid="stAppViewContainer"] .main { margin-left: 0 !important; }

        .block-container{
          padding-top: 1.1rem !important;
          padding-bottom: 120px !important;
          max-width: 1200px !important;
        }

        :root{
          --bg: #f6f8fc;
          --card: #ffffff;
          --text: #0b1220;
          --muted: rgba(11,18,32,.65);
          --border: rgba(11,18,32,.10);
          --shadow: 0 10px 28px rgba(11,18,32,.10);
          --blue: #1b4cff;   /* O2 modrá */
          --blue2:#0e2aa8;   /* tmavší O2 */
          --radius: 18px;
        }

        /* =========================================================
           2) INPUTY + LABELY
           ========================================================= */
        label[data-testid="stWidgetLabel"]{
          color: var(--text) !important;
          font-weight: 850 !important;
          font-size: 14px !important;
          margin-bottom: 6px !important;
        }

        input, textarea{ color: var(--text) !important; }

        input::placeholder, textarea::placeholder{
          color: rgba(11,18,32,.40) !important;
        }

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div{
          border-radius: 14px !important;
          border: 1px solid rgba(11,18,32,.12) !important;
          background: #fff !important;
          box-shadow: 0 6px 16px rgba(11,18,32,.06) !important;
        }

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within{
          border-color: rgba(27,76,255,.55) !important;
          box-shadow: 0 0 0 4px rgba(27,76,255,.14) !important;
        }

        /* =========================================================
           3) TABS
           ========================================================= */
        [data-testid="stTabs"]{ margin-top: 6px !important; }

        [data-testid="stTabs"] button{
          color: rgba(11,18,32,.60) !important;
          font-weight: 900 !important;
          font-size: 15px !important;
        }

        [data-testid="stTabs"] button[aria-selected="true"]{
          color: var(--blue) !important;
        }

        [data-testid="stTabs"] [data-baseweb="tab-highlight"]{
          background: var(--blue) !important;
          height: 3px !important;
          border-radius: 999px !important;
        }

        /* =========================================================
           4) BUTTONS – O2 MODRÁ (FIX PRO FORM SUBMIT)
           ========================================================= */
        .stButton > button,
        .stFormSubmitButton > button{
          border-radius: 999px !important;
          font-weight: 900 !important;
          height: 46px !important;
          transition: all .15s ease !important;
        }

        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"],
        button[data-testid="baseButton-primary"],
        button[data-testid="stBaseButton-primary"]{
          background: var(--blue) !important;
          color: #fff !important;
          border: 0 !important;
          box-shadow: 0 10px 28px rgba(11,18,32,.14) !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover,
        button[data-testid="baseButton-primary"]:hover{
          background: var(--blue2) !important;
          transform: translateY(-1px);
        }

        .stButton > button[kind="secondary"],
        .stFormSubmitButton > button[kind="secondary"],
        button[data-testid="baseButton-secondary"]{
          background: #fff !important;
          color: var(--text) !important;
          border: 1px solid var(--border) !important;
          box-shadow: 0 6px 16px rgba(11,18,32,.08) !important;
        }

        /* =========================================================
           5) CARD
           ========================================================= */
        .o2-card{
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          padding: 16px;
          margin: 12px 0 16px 0;
        }

        .o2-card-title{
          font-size: 18px;
          font-weight: 950;
          margin-bottom: 6px;
        }

        .o2-muted{
          color: var(--muted);
          font-size: 13px;
        }

        /* =========================================================
           6) HERO
           ========================================================= */
        .o2-hero{
          border-radius: 28px;
          background: linear-gradient(135deg, var(--blue2), var(--blue));
          padding: 34px;
          min-height: 220px;
          box-shadow: 0 18px 50px rgba(11,18,32,.18);
          margin-bottom: 16px;
        }

        .o2-hero h1{
          margin:0;
          font-size: 44px;
          color: #fff;
          font-weight: 950;
        }

        .o2-hero p{
          margin-top: 10px;
          color: rgba(255,255,255,.88);
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
          <h1>{title}</h1>
          <p>{subtitle}</p>
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