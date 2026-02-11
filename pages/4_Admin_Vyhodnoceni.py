# pages/4_Admin_Vyhodnoceni.py
import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu


# =====================
# BODY – jednotný výpočet (zápasy + umístění + manuální)
# =====================
def recompute_profiles_points(supabase, user_ids: list[str]):
    """Přepíše profiles.points pro dané uživatele podle:
    predictions.points_awarded + placement_predictions.points_awarded + sum(manual_points_log.change_amount).
    """
    if not user_ids:
        return

    # --- zápasy ---
    match_sum: dict[str, int] = {uid: 0 for uid in user_ids}
    try:
        preds = (
            supabase.table("predictions")
            .select("user_id, points_awarded")
            .in_("user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in preds:
            uid = r.get("user_id")
            if uid in match_sum:
                match_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass

    # --- umístění ---
    place_sum: dict[str, int] = {uid: 0 for uid in user_ids}
    try:
        pp = (
            supabase.table("placement_predictions")
            .select("user_id, points_awarded")
            .in_("user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in pp:
            uid = r.get("user_id")
            if uid in place_sum:
                place_sum[uid] += int(r.get("points_awarded") or 0)
    except Exception:
        pass

    # --- manuální ---
    manual_sum: dict[str, int] = {uid: 0 for uid in user_ids}
    try:
        logs = (
            supabase.table("manual_points_log")
            .select("target_user_id, change_amount")
            .in_("target_user_id", user_ids)
            .execute()
            .data
            or []
        )
        for r in logs:
            uid = r.get("target_user_id")
            if uid in manual_sum:
                manual_sum[uid] += int(r.get("change_amount") or 0)
    except Exception:
        pass

    errors = []
    for uid in user_ids:
        total = int(match_sum.get(uid, 0)) + int(place_sum.get(uid, 0)) + int(manual_sum.get(uid, 0))
        if total < 0:
            total = 0
        try:
            supabase.table("profiles").update({"points": total}).eq("user_id", uid).execute()
        except Exception as e:
            errors.append(f"{uid}: {e}")

    if errors:
        st.error("Některé updates do profiles selhaly (RLS/permissions):")
        st.code("\n".join(errors))


# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Vyhodnocení zápasů (Admin)", page_icon="🧮", layout="wide")

apply_o2_style()

# Lokální CSS jen pro tuhle stránku (selectboxy + expandery + tabulka)
st.markdown(
    """
    <style>
      [data-baseweb="select"] > div{
        background: #fff !important;
        border: 1px solid rgba(11,18,32,.12) !important;
        border-radius: 14px !important;
        box-shadow: 0 6px 16px rgba(11,18,32,.06) !important;
      }
      [data-baseweb="select"] div, [data-baseweb="select"] span{
        color: #0b1220 !important;
        font-weight: 650 !important;
      }
      [data-baseweb="select"] > div:focus-within{
        border-color: rgba(27,76,255,.55) !important;
        box-shadow: 0 0 0 4px rgba(27,76,255,.14) !important;
      }

      [data-testid="stExpander"]{
        border: 1px solid rgba(11,18,32,.10) !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        background: #fff !important;
        box-shadow: 0 10px 28px rgba(11,18,32,.08) !important;
      }
      [data-testid="stExpander"] summary{
        background: rgba(246,248,252,.9) !important;
        padding: 10px 14px !important;
        font-weight: 800 !important;
        color: #0b1220 !important;
      }
      [data-testid="stExpander"] summary:hover{
        background: rgba(27,76,255,.06) !important;
      }

      [data-testid="stDataFrame"]{
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 1px solid rgba(11,18,32,.10) !important;
        box-shadow: 0 10px 28px rgba(11,18,32,.08) !important;
        background: #fff !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================
# Supabase klient
# =====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY v .env / Secrets")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ✅ Navázání session (nutné pro RLS)
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
    if st.button("Jít na přihlášení", type="primary"):
        st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# =====================
# Ověření admina
# =====================
try:
    prof = (
        supabase.table("profiles")
        .select("user_id, email, is_admin")
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    profile = prof.data
except Exception as e:
    st.error(f"Nelze načíst profil: {e}")
    st.stop()

if not profile or not profile.get("is_admin"):
    st.error("Nemáš admin práva.")
    st.stop()

# =====================
# HERO
# =====================
render_hero(
    "Admin – Vyhodnocení zápasů",
    "Zadáš výsledek po základní době a označíš, kteří tipovaní střelci dali gól. Poté se přepočítají body.",
    image_path=None,
)

# =====================
# Admin box s odkazy
# =====================
with card("🛠️ Admin odkazy"):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("🧾 Soupisky", type="secondary", use_container_width=True, key="admin_links_soupisky"):
            st.switch_page("pages/1_Soupisky_Admin.py")
    with c2:
        if st.button("✏️ Manuální body", type="primary", use_container_width=True, key="admin_links_manual"):
            st.switch_page("pages/8_Admin_Manualni_Body.py")
    with c3:
        if st.button("🏅 Umístění", type="secondary", use_container_width=True, key="admin_links_umisteni"):
            st.switch_page("pages/7_Admin_Umisteni.py")
    with c4:
        if st.button("🔍 Diagnostika", type="secondary", use_container_width=True, key="admin_links_diag"):
            st.switch_page("pages/6_Admin_Diagnostika_RLS.py")
    with c5:
        if st.button("🔄 Sync bodů", type="secondary", use_container_width=True, key="admin_links_sync"):
            st.switch_page("pages/5_Admin_Sync_Points.py")

# =====================
# Load matches
# =====================
try:
    matches_res = (
        supabase.table("matches")
        .select("id, home_team, away_team, starts_at, final_home_score, final_away_score, evaluated_at")
        .order("starts_at")
        .execute()
    )
    matches = matches_res.data or []
except Exception as e:
    st.error(f"Nelze načíst zápasy: {e}")
    st.stop()

if not matches:
    st.info("V databázi nejsou žádné zápasy.")
    st.stop()


def match_label(m: dict) -> str:
    fin_h = m.get("final_home_score")
    fin_a = m.get("final_away_score")
    res = f"{fin_h}:{fin_a}" if fin_h is not None and fin_a is not None else "—"
    return f"{m['home_team']} vs {m['away_team']} | výsledek: {res} | {m.get('starts_at','')}"


match_map = {match_label(m): m for m in matches}

with card("Vyber zápas", "Vyber konkrétní zápas, který chceš vyhodnotit."):
    selected_label = st.selectbox("Zápas", list(match_map.keys()), label_visibility="collapsed")

m = match_map[selected_label]
match_id = m["id"]  # BIGINT

# =====================
# Load predictions for match
# =====================
try:
    preds_res = (
        supabase.table("predictions")
        .select("user_id, match_id, home_score, away_score, scorer_player_id, scorer_name, scorer_team, points_awarded")
        .eq("match_id", match_id)
        .execute()
    )
    preds = preds_res.data or []
except Exception as e:
    st.error(f"Nelze načíst tipy: {e}")
    st.stop()

# user_id -> email map
user_emails = {}
if preds:
    uids = list({p["user_id"] for p in preds if p.get("user_id")})
    try:
        profs = (
            supabase.table("profiles")
            .select("user_id, email")
            .in_("user_id", uids)
            .execute()
        )
        for r in (profs.data or []):
            user_emails[r["user_id"]] = r.get("email") or r["user_id"]
    except Exception:
        user_emails = {}

# =====================
# Load scorer decisions (scorer_results) for match
# =====================
try:
    sr_res = (
        supabase.table("scorer_results")
        .select("scorer_player_id, scorer_name, scorer_team, did_score")
        .eq("match_id", match_id)
        .execute()
    )
    scorer_results = sr_res.data or []
except Exception:
    scorer_results = []

sr_map = {r["scorer_player_id"]: r for r in scorer_results if r.get("scorer_player_id")}

# =====================
# UI: výsledek zápasu
# =====================
with card("Zápas", "Nastav výsledek po základní době."):
    col1, col2, col3 = st.columns([1, 1, 1.2], gap="large")

    default_home = int(m.get("final_home_score") or 0)
    default_away = int(m.get("final_away_score") or 0)

    with col1:
        final_home = st.number_input(
            f"{m['home_team']} (domácí)",
            min_value=0,
            max_value=99,
            value=default_home,
            step=1,
        )
    with col2:
        final_away = st.number_input(
            f"{m['away_team']} (hosté)",
            min_value=0,
            max_value=99,
            value=default_away,
            step=1,
        )
    with col3:
        st.write("")
        st.write("")
        save_match = st.button("💾 Uložit výsledek", type="primary", use_container_width=True)

# =====================
# Zapsat výsledek do matches
# =====================
if save_match:
    try:
        supabase.table("matches").update(
            {
                "final_home_score": int(final_home),
                "final_away_score": int(final_away),
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", match_id).execute()
        st.success("✅ Výsledek uložen.")
        st.rerun()
    except Exception as e:
        st.error(f"Chyba při ukládání výsledku: {e}")

# =====================
# Tipovaní střelci – rozhodnutí admina
# =====================
unique_scorers = {}
for p in preds:
    pid = p.get("scorer_player_id")
    if pid and pid not in unique_scorers:
        unique_scorers[pid] = {
            "scorer_player_id": pid,
            "scorer_name": p.get("scorer_name") or "—",
            "scorer_team": p.get("scorer_team") or "—",
        }

with card("⚽ Tipovaní střelci", "U každého střelce rozhodni, jestli dal gól (ano/ne)."):
    if not unique_scorers:
        st.info("Nikdo netipoval střelce pro tento zápas.")
    else:
        st.caption("Admin rozhodne: dal / nedal. (Ukládá se do scorer_results.)")

        for pid, info in unique_scorers.items():
            current = sr_map.get(pid, {})
            did_score_default = bool(current.get("did_score")) if current else False

            who = []
            for p in preds:
                if p.get("scorer_player_id") == pid:
                    who.append(user_emails.get(p["user_id"], p["user_id"]))

            title = f"{info['scorer_name']} ({info['scorer_team']}) — tipů: {len(who)}"

            with st.expander(title, expanded=False):
                c1, c2 = st.columns([1, 3], gap="large")
                with c1:
                    did_score = st.checkbox("Dal gól ✅", value=did_score_default, key=f"did_{pid}")
                with c2:
                    st.write("**Kdo ho tipoval:**")
                    for e in who:
                        st.write(f"• {e}")

                if st.button("Uložit rozhodnutí", key=f"save_sr_{pid}", type="primary"):
                    try:
                        payload = {
                            "match_id": match_id,
                            "scorer_player_id": pid,
                            "scorer_name": info["scorer_name"],
                            "scorer_team": info["scorer_team"],
                            "did_score": bool(did_score),
                        }
                        supabase.table("scorer_results").upsert(payload).execute()
                        st.success("Uloženo ✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Chyba při ukládání: {e}")

# =====================
# Náhled bodů (pouze UI)
# =====================
with card("🧾 Náhled bodů", "Kontrola: jak se body počítají pro jednotlivé tipy."):
    if not preds:
        st.info("Pro tento zápas nejsou žádné tipy.")
    else:
        rows = []
        for p in preds:
            rows.append(
                {
                    "Uživatel": user_emails.get(p["user_id"], p["user_id"]),
                    "Tip": f"{p.get('home_score','—')}:{p.get('away_score','—')}",
                    "Střelec": p.get("scorer_name") or "—",
                    "Body (v DB)": p.get("points_awarded"),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


# =====================
# HELPERS
# =====================
def score_points(pred_h, pred_a, final_h, final_a):
    points = 0
    detail = {
        "exact_score": 0,
        "winner_and_diff": 0,
        "winner_only": 0,
        "one_team_goals": 0,
        "scorer": 0,
    }

    # přesný výsledek
    if pred_h == final_h and pred_a == final_a:
        points += 6
        detail["exact_score"] = 6
        return points, detail

    pred_diff = pred_h - pred_a
    final_diff = final_h - final_a
    pred_winner = 1 if pred_diff > 0 else (-1 if pred_diff < 0 else 0)
    final_winner = 1 if final_diff > 0 else (-1 if final_diff < 0 else 0)

    # správný vítěz + rozdíl
    if pred_winner == final_winner and pred_diff == final_diff:
        points += 4
        detail["winner_and_diff"] = 4
    # správný vítěz (ne remíza)
    elif pred_winner == final_winner and pred_winner != 0:
        points += 2
        detail["winner_only"] = 2

    # góly aspoň jednoho týmu přesně
    if pred_h == final_h or pred_a == final_a:
        points += 1
        detail["one_team_goals"] = 1

    return points, detail


def scorer_point_for_prediction(pred: dict, did_score_map: dict) -> int:
    """✅ střelec je za 5 bodů"""
    pid = pred.get("scorer_player_id")
    if not pid:
        return 0
    return 5 if did_score_map.get(pid) else 0


# =====================
# ACTIONS
# =====================
with card("⚙️ Akce", "Spusť přepočet bodů nebo smaž hodnocení zápasu."):
    colA, colB = st.columns([1, 1], gap="large")
    with colA:
        do_recalc = st.button("🔄 Přepočítat body", type="primary", use_container_width=True)
    with colB:
        do_delete_eval = st.button("🗑️ Smazat hodnocení zápasu", type="secondary", use_container_width=True)

# =====================
# Přepočet bodů
# =====================
if do_recalc:
    try:
        # 1) natáhni ČERSTVÝ výsledek zápasu z DB
        match_row = (
            supabase.table("matches")
            .select("final_home_score, final_away_score")
            .eq("id", match_id)
            .single()
            .execute()
            .data
            or {}
        )
        if match_row.get("final_home_score") is None or match_row.get("final_away_score") is None:
            st.error("Nejdřív nastav výsledek zápasu.")
            st.stop()

        final_h = int(match_row.get("final_home_score") or 0)
        final_a = int(match_row.get("final_away_score") or 0)

        # 2) načti rozhodnutí střelců
        sr_res2 = (
            supabase.table("scorer_results")
            .select("scorer_player_id, did_score")
            .eq("match_id", match_id)
            .execute()
        )
        did_score_map = {
            r["scorer_player_id"]: bool(r.get("did_score"))
            for r in (sr_res2.data or [])
            if r.get("scorer_player_id") is not None
        }

        # 3) přepočti body pro každý tip
        updates = []
        for p in preds:
            ph = int(p.get("home_score") or 0)
            pa = int(p.get("away_score") or 0)

            sp, detail = score_points(ph, pa, final_h, final_a)

            # ✅ +5 bodů za správného střelce
            sp += scorer_point_for_prediction(p, did_score_map)
            if p.get("scorer_player_id") and did_score_map.get(p["scorer_player_id"]):
                detail["scorer"] = 5

            updates.append(
                {
                    "user_id": p["user_id"],
                    "match_id": p["match_id"],
                    "points_awarded": int(sp),
                    "points_detail": detail,
                }
            )

        # 4) ✅ FIX: update jen bodů + detailu (NE upsert)
        for u in updates:
            supabase.table("predictions").update(
                {
                    "points_awarded": u["points_awarded"],
                    "points_detail": u["points_detail"],
                }
            ).eq("user_id", u["user_id"]).eq("match_id", u["match_id"]).execute()

        # 5) označ zápas jako vyhodnocený
        supabase.table("matches").update(
            {"evaluated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", match_id).execute()

        # 6) přepočti profiles.points (leaderboard celkem)
        uids = list({p["user_id"] for p in preds if p.get("user_id")})
        recompute_profiles_points(supabase, uids)

        st.success("✅ Body přepočítány a uloženy.")
        st.rerun()

    except Exception as e:
        st.error(f"Chyba při přepočtu: {e}")

# =====================
# Mazání hodnocení
# =====================
if do_delete_eval:
    with card("⚠️ Potvrzení", "Tímto smažeš body za zápas a vrátíš ho do stavu 'nevyhodnoceno'."):
        confirm = st.checkbox("Rozumím, chci smazat hodnocení tohoto zápasu.", value=False)

        if st.button("Ano, smaž hodnocení", type="primary", disabled=not confirm):
            try:
                preds_before = (
                    supabase.table("predictions")
                    .select("user_id")
                    .eq("match_id", match_id)
                    .execute()
                ).data or []

                affected_uids = list({p.get("user_id") for p in preds_before if p.get("user_id")})

                supabase.table("predictions").update(
                    {"points_awarded": 0, "points_detail": None}
                ).eq("match_id", match_id).execute()

                supabase.table("scorer_results").delete().eq("match_id", match_id).execute()

                recompute_profiles_points(supabase, affected_uids)

                supabase.table("matches").update(
                    {"evaluated_at": None}
                ).eq("id", match_id).execute()

                st.success("🗑️ Hodnocení zápasu bylo smazáno. Zápas je zpět jako 'nevyhodnocený'.")
                st.rerun()

            except Exception as e:
                st.error(f"Chyba při mazání hodnocení: {e}")