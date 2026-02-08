import streamlit as st
import base64
from pathlib import Path

def _img_to_base64(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = p.read_bytes()
    return base64.b64encode(data).decode("utf-8")

def apply_o2_style():
    st.markdown(
        """
        <style>
          /* --- Reset Streamlit chromu --- */
          header[data-testid="stHeader"] { display:none; }
          [data-testid="stSidebarNav"] { display:none; }
          .block-container { padding-top: 1.2rem; max-width: 1200px; }

          /* --- O2-like design tokens --- */
          :root{
            --bg: #f6f8fc;
            --card: #ffffff;
            --text: #0b1220;
            --muted: rgba(11,18,32,.65);
            --border: rgba(11,18,32,.08);
            --shadow: 0 8px 24px rgba(11,18,32,.08);
            --blue: #1b4cff;
            --blue2:#0e2aa8;
            --radius: 18px;
          }

          html, body, [data-testid="stAppViewContainer"]{
            background: var(--bg) !important;
            color: var(--text);
          }

          /* Buttons */
          button[kind="primary"]{
            background: var(--blue) !important;
            border: 0 !important;
            border-radius: 999px !important;
            padding: 10px 16px !important;
            box-shadow: var(--shadow);
          }
          button[kind="secondary"]{
            border-radius: 999px !important;
          }

          /* Card */
          .o2-card{
            background: var(--card);
            border: 1px solid var(--border);
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
          .o2-muted{ color: var(--muted); font-size: 13px; }

          /* Hero */
          .o2-hero{
            border-radius: 28px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,.35);
            box-shadow: 0 18px 50px rgba(11,18,32,.18);
            background: linear-gradient(135deg, var(--blue2), var(--blue));
            position: relative;
            padding: 34px 34px;
            min-height: 220px;
            margin-bottom: 18px;
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
            max-width: 620px;
          }
          .o2-hero-img{
            width: 360px;
            max-width: 40vw;
            height: 220px;
            border-radius: 22px;
            background-size: cover;
            background-position: center;
            box-shadow: 0 18px 50px rgba(0,0,0,.25);
          }

          /* Quick tiles */
          .o2-tiles{
            display:grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 14px;
            margin: 10px 0 18px 0;
          }
          .o2-tile{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 16px;
            min-height: 92px;
            display:flex;
            flex-direction: column;
            justify-content: center;
            gap: 8px;
          }
          .o2-tile-ico{ font-size: 22px; }
          .o2-tile-title{ font-weight: 900; }
          @media (max-width: 980px){
            .o2-tiles{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .o2-hero h1{ font-size: 34px; }
            .o2-hero-img{ width: 100%; max-width: 100%; }
          }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_hero(title: str, subtitle: str, image_path: str | None = None):
    img_style = ""
    if image_path:
        b64 = _img_to_base64(image_path)
        if b64:
            img_style = f"background-image:url('data:image/png;base64,{b64}');"
    hero_html = f"""
      <div class="o2-hero">
        <div class="o2-hero-grid">
          <div style="min-width:320px;flex:1">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div class="o2-hero-img" style="{img_style}"></div>
        </div>
      </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

def tiles(items):
    # items: list of (icon, title, page_path)
    st.markdown('<div class="o2-tiles">', unsafe_allow_html=True)
    cols = st.columns(len(items))
    # jednodušší: vykreslit přes markdown + buttony nejde ideálně,
    # takže to uděláme jako grid přes HTML + odkazy jen vizuálně (nebo pak přepojíme na st.switch_page přes st.button).
    st.markdown("</div>", unsafe_allow_html=True)

def card(title: str, subtitle: str | None = None):
    st.markdown('<div class="o2-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="o2-card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="o2-muted">{subtitle}</div>', unsafe_allow_html=True)
    return _CardCtx()

class _CardCtx:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        st.markdown("</div>", unsafe_allow_html=True)