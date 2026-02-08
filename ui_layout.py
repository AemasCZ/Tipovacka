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
           1) ZÁKLAD
           ========================================================= */
        section[data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display:none !important; }

        html, body, [data-testid="stAppViewContainer"]{
          background: #f6f8fc !important;
          color: #0b1220 !important;
        }

        .block-container{
          padding-top: 1.1rem !important;
          max-width: 1200px !important;
        }

        :root{
          --blue: #1b4cff;
          --blue2:#0e2aa8;
          --text: #0b1220;
          --border: rgba(11,18,32,.10);
          --shadow: 0 10px 28px rgba(11,18,32,.10);
        }

        /* =========================================================
           2) INPUTY + LABELY
           ========================================================= */
        label[data-testid="stWidgetLabel"]{
          font-weight: 850 !important;
          font-size: 14px !important;
        }

        [data-baseweb="input"] > div{
          border-radius: 14px !important;
          background: #fff !important;
        }

        /* =========================================================
           3) TABS
           ========================================================= */
        [data-testid="stTabs"] button{
          font-weight: 900 !important;
        }
        [data-testid="stTabs"] button[aria-selected="true"]{
          color: var(--blue) !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"]{
          background: var(--blue) !important;
        }

        /* =========================================================
           4) BUTTONS – FIX NA ČERNÉ TLAČÍTKO
           ========================================================= */
        .stButton > button{
          border-radius: 999px !important;
          font-weight: 800 !important;
        }

        /* PRIMARY */
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

        /* 🔑 TADY JE TEN FIX */
        .stButton > button[kind="primary"]:disabled{
          background: rgba(27,76,255,.45) !important;
          color: #fff !important;
          opacity: 1 !important;
          box-shadow: none !important;
          cursor: not-allowed !important;
        }

        /* SECONDARY */
        .stButton > button[kind="secondary"]{
          background: #fff !important;
          color: var(--text) !important;
          border: 1px solid var(--border) !important;
        }

        /* =========================================================
           5) CARD
           ========================================================= */
        .o2-card{
          background: #fff;
          border: 1px solid var(--border);
          border-radius: 18px;
          box-shadow: var(--shadow);
          padding: 16px;
          margin: 12px 0;
        }

        /* =========================================================
           6) HERO
           ========================================================= */
        .o2-hero{
          border-radius: 28px;
          background: linear-gradient(135deg, var(--blue2), var(--blue));
          padding: 34px;
          color: #fff;
          margin-bottom: 16px;
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
    st.markdown(f"<strong>{title}</strong>", unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)
    return _CardCtx()


class _CardCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        st.markdown("</div>", unsafe_allow_html=True)