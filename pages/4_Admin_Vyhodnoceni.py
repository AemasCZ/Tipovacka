# pages/4_Admin_Vyhodnoceni.py
import os
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv

from ui_layout import apply_o2_style, render_hero, card
from ui_menu import render_top_menu

load_dotenv()
st.set_page_config(page_title="Admin – Vyhodnocení zápasů", page_icon="🧮", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("Chybí SUPABASE_URL nebo SUPABASE_ANON_KEY")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

if st.session_state.get("access_token") and st.session_state.get("refresh_token"):
    supabase.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])

apply_o2_style()

user = st.session_state.get("user")
user_id = user["id"] if user else None
render_top_menu(user, supabase=supabase, user_id=user_id)

render_hero(
    "Admin – Vyhodnocení zápasů",
    "Zadáš výsledek po základní době + označíš, kdo dal gól. Systém rozdá body do predictions.points_awarded.",
    image_path="assets/olymp.png",
)

if not user:
    with card("🔐 Nepřihlášen"):
        st.warning("Nejsi přihlášený.")
        if st.button("➡️ Přihlášení", type="primary"):
            st.switch_page("app.py")
    st.stop()

if not st.session_state.get("access_token") or not st.session_state.get("refresh_token"):
    st.error("Chybí session tokeny. Odhlas se a přihlas znovu.")
    st.stop()

# Ověření admina
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
    st.error("Tato stránka je jen pro admina.")
    st.stop()

def outcome(h: int, a: int) -> int:
    if h > a:
        return 1
    if h < a:
        return -1
    return 0

def calc_points(ph: int, pa: int, ah: int, aa: int, scorer_ok: bool) -> tuple[int, dict]:
    """
    - přesný výsledek = 6
    - správný vítěz + správný rozdíl = 4
    - správný vítěz = 3
    - trefený počet gólů jednoho týmu = 1
    - trefený střelec = 5
    - max 11
    """
    detail = {"exact_score": 0, "winner_and_diff": 0, "winner_only": 0, "one_team_goals": 0, "scorer": 0}
    base = 0

    if ph == ah and pa == aa:
        detail["exact_score"] = 6
        base = 6
    else:
        pred_out = outcome(ph, pa)
        act_out = outcome(ah, aa)

        pred_diff = ph - pa
        act_diff = ah - aa

        correct_winner = (pred_out == act_out)
        correct_diff = (pred_diff == act_diff)

        if correct_winner and correct_diff:
            detail["winner_and_diff"] = 4
            base = 4
        elif correct_winner:
            detail["winner_only"] = 3
            base = 3

        if (ph == ah) or (pa == aa):
            detail["one_team_goals"] = 1
            base += 1

        base = min(base, 6)

    scorer_pts = 5 if scorer_ok else 0
    detail["scorer"] = scorer_pts
    total = min(base + scorer_pts, 11)
    detail["total"] = total
    return total, detail

# Load matches
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
    with card("ℹ️ Info"):
        st.info("V databázi nejsou žádné zápasy.")
    st.stop()

def match_label(m: dict) -> str:
    fin_h = m.get("final_home_score")
    fin_a = m.get("final_away_score")
    res = f"{fin_h}:{fin_a}" if fin_h is not None and fin_a is not None else "—"
    return f"{m['home_team']} vs {m['away_team']} | výsledek: {res} | {m.get('starts_at','')}"

match_map = {match_label(m): m for m in matches}
selected_label = st.selectbox("Vyber zápas", list(match_map.keys()))
m = match_map[selected_label]
match_id = m["id"]

# Load predictions for match
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

user_emails = {}
if preds:
    uids = list({p["user_id"] for p in preds if p.get("user_id")})
    try:
        profs = supabase.table("profiles").select("user_id, email").in_("user_id", uids).execute()
        for r in (profs.data or []):
            user_emails[r["user_id"]] = r.get("email") or r["user_id"]
    except Exception:
        pass

with card("🏒 Zápas", "Nastav výsledek po základní době."):
    c1, c2, c3 = st.columns([1, 1, 1.2], vertical_alignment="bottom")

    default_h = 0 if m.get("final_home_score") is None else int(m["final_home_score"])
    default_a = 0 if m.get("final_away_score") is None else int(m["final_away_score"])

    with c1:
        final_home = st.number_input(m["home_team"], min_value=0, max_value=20, value=default_h, step=1)

    with c2:
        final_away = st.number_input(m["away_team"], min_value=0, max_value=20, value=default_a, step=1)

# Existing scorer_results
existing_scorers = {}
try:
    sr_res = supabase.table("scorer_results").select(
        "scorer_player_id, scorer_name, scorer_team, did_score"
    ).eq("match_id", match_id).execute()
    for r in (sr_res.data or []):
        key = (str(r.get("scorer_player_id") or ""), r.get("scorer_name") or "", (r.get("scorer_team") or "").strip())
        existing_scorers[key] = bool(r.get("did_score"))
except Exception:
    pass

# Group tipovaní střelci
scorer_groups = {}
for p in preds:
    sname = (p.get("scorer_name") or "").strip()
    if not sname:
        continue
    team = (p.get("scorer_team") or "").strip()
    pid = str(p.get("scorer_player_id") or "")
    key = (pid, sname, team)
    scorer_groups.setdefault(key, []).append(p)

scorer_state = {}

with card("⚽ Tipovaní střelci", "Admin rozhodne: dal / nedal."):
    if not scorer_groups:
        st.info("Nikdo zatím netipoval střelce u tohoto zápasu.")
    else:
        for key, plist in scorer_groups.items():
            pid, name, team = key
            prev = existing_scorers.get(key, False)
            with st.expander(f"{name} ({team}) — tipů: {len(plist)}", expanded=True):
                scorer_state[key] = st.checkbox("✅ Dal gól v tomto zápase", value=prev, key=f"sc_{match_id}_{pid}_{name}_{team}")
                st.caption("Kdo ho tipoval:")
                for p in plist:
                    email = user_emails.get(p["user_id"], p["user_id"])
                    st.write(f"- {email} (tip: {int(p.get('home_score') or 0)}:{int(p.get('away_score') or 0)})")

with card("🧾 Náhled bodů"):
    preview_rows = []
    for p in preds:
        ph = int(p.get("home_score") or 0)
        pa = int(p.get("away_score") or 0)

        sname = (p.get("scorer_name") or "").strip()
        if sname:
            skey = (str(p.get("scorer_player_id") or ""), sname, (p.get("scorer_team") or "").strip())
            scorer_ok = bool(scorer_state.get(skey, existing_scorers.get(skey, False)))
        else:
            scorer_ok = False

        pts, detail = calc_points(ph, pa, int(final_home), int(final_away), scorer_ok)
        old_pts = int(p.get("points_awarded") or 0)
        email = user_emails.get(p["user_id"], p["user_id"])
        preview_rows.append({"Uživatel": email, "Tip": f"{ph}:{pa}", "Střelec": sname or "—", "Body": pts, "Původně": old_pts, "Δ": pts - old_pts, "Detail": str(detail)})

    if preview_rows:
        st.dataframe(preview_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Zatím nikdo netipoval výsledek pro tento zápas.")

with card("💾 Uložit výsledek + přepočítat body"):
    if st.button("Uložit a přepočítat", type="primary", use_container_width=True):
        errors = []
        steps = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1) matches
        try:
            supabase.table("matches").update(
                {"final_home_score": int(final_home), "final_away_score": int(final_away), "evaluated_at": now_iso}
            ).eq("id", match_id).execute()
            steps.append("✅ Výsledek uložen do matches")
        except Exception as e:
            errors.append(f"❌ matches update: {e}")

        # 2) scorer_results
        try:
            supabase.table("scorer_results").delete().eq("match_id", match_id).execute()
            steps.append("✅ scorer_results smazáno")
        except Exception as e:
            errors.append(f"⚠️ scorer_results delete: {e}")

        payload = []
        for key, did in scorer_state.items():
            pid, name, team = key
            payload.append({"match_id": match_id, "scorer_player_id": pid if pid else None, "scorer_name": name, "scorer_team": team or None, "did_score": bool(did)})

        if payload:
            try:
                supabase.table("scorer_results").insert(payload).execute()
                steps.append(f"✅ scorer_results vloženo ({len(payload)})")
            except Exception as e:
                errors.append(f"❌ scorer_results insert: {e}")

        # 3) predictions points
        updated = 0
        failed = 0
        for p in preds:
            try:
                ph = int(p.get("home_score") or 0)
                pa = int(p.get("away_score") or 0)

                sname = (p.get("scorer_name") or "").strip()
                if sname:
                    skey = (str(p.get("scorer_player_id") or ""), sname, (p.get("scorer_team") or "").strip())
                    scorer_ok = bool(scorer_state.get(skey, False))
                else:
                    scorer_ok = False

                new_pts, detail = calc_points(ph, pa, int(final_home), int(final_away), scorer_ok)

                supabase.table("predictions").update(
                    {"points_awarded": int(new_pts), "evaluated_at": now_iso, "points_detail": detail}
                ).eq("user_id", p["user_id"]).eq("match_id", match_id).execute()

                updated += 1
            except Exception as e:
                failed += 1
                email = user_emails.get(p.get("user_id"), "unknown")
                errors.append(f"⚠️ tip update {email}: {e}")

        if updated:
            steps.append(f"✅ Aktualizováno tipů: {updated}")
        if failed:
            errors.append(f"⚠️ Selhalo tipů: {failed}")

        for s in steps:
            st.success(s)
        for e in errors:
            st.error(e)

        if not errors:
            st.balloons()
            st.success("Hotovo 🎉")
            st.info("Leaderboard se počítá živě. Pokud chceš sync do profiles.points, použij Admin Sync.")