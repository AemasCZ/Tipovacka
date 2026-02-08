import os
from datetime import datetime, timezone

import streamlit as st
from supabase import create_client
from dotenv import load_dotenv
from ui_menu import render_top_menu

# =====================
# Nastavení stránky
# =====================
load_dotenv()
st.set_page_config(page_title="Vyhodnocení zápasů (Admin)", page_icon="🧮", layout="wide")

# =====================
# CSS
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
    if st.button("Jít na přihlášení"):
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
    st.error("Tato stránka je jen pro admina.")
    st.stop()

# =====================
# Scoring logika
# =====================
def outcome(h: int, a: int) -> int:
    if h > a:
        return 1
    if h < a:
        return -1
    return 0

def calc_points(ph: int, pa: int, ah: int, aa: int, scorer_ok: bool) -> tuple[int, dict]:
    """
    Pravidla:
    - Přesný výsledek = 6 bodů
    - Správný vítěz + správný brankový rozdíl = 4 body
    - Správně určený vítěz = 3 body
    - Trefený počet gólů jednoho týmu = 1 bod
    - Trefený střelec = 5 bodů
    - max 11
    Platí po základní hrací době.
    """
    detail = {
        "exact_score": 0,
        "winner_and_diff": 0,
        "winner_only": 0,
        "one_team_goals": 0,
        "scorer": 0,
    }

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

        # trefený počet gólů jednoho týmu (aspoň jeden sedí)
        if (ph == ah) or (pa == aa):
            detail["one_team_goals"] = 1
            base += 1

        # pojistka: základ bez střelce max 6
        base = min(base, 6)

    scorer_pts = 5 if scorer_ok else 0
    detail["scorer"] = scorer_pts

    total = min(base + scorer_pts, 11)
    detail["total"] = total
    return total, detail

# =====================
# UI
# =====================
st.title("🧮 Vyhodnocení zápasů (Admin)")
st.caption("Zadáš výsledek po základní době a označíš, kteří tipovaní střelci dali gól. Poté se přepočítají body.")

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
selected_label = st.selectbox("Vyber zápas", list(match_map.keys()))
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
            .select("user_id, email, points")
            .in_("user_id", uids)
            .execute()
        )
        for r in (profs.data or []):
            user_emails[r["user_id"]] = r.get("email") or r["user_id"]
    except Exception:
        pass

# =====================
# Card: match result inputs
# =====================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader(f"🏒 {m['home_team']} vs {m['away_team']}")
st.markdown('<div class="muted">Platí výsledek po základní hrací době (může být remíza).</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 1, 1.2], vertical_alignment="bottom")

default_h = 0 if m.get("final_home_score") is None else int(m["final_home_score"])
default_a = 0 if m.get("final_away_score") is None else int(m["final_away_score"])

with c1:
    st.markdown(f"**Skutečný počet gólů domácí**")
    final_home = st.number_input(
        m['home_team'],
        min_value=0,
        max_value=20,
        value=default_h,
        step=1,
        key=f"final_home_{match_id}",
        label_visibility="collapsed",
    )

with c2:
    st.markdown(f"**Skutečný počet gólů hosté**")
    final_away = st.number_input(
        m['away_team'],
        min_value=0,
        max_value=20,
        value=default_a,
        step=1,
        key=f"final_away_{match_id}",
        label_visibility="collapsed",
    )

st.markdown("</div>", unsafe_allow_html=True)

# =====================
# Load existing scorer_results
# =====================
existing_scorers = {}
try:
    sr_res = (
        supabase.table("scorer_results")
        .select("scorer_player_id, scorer_name, scorer_team, did_score")
        .eq("match_id", match_id)
        .execute()
    )
    for r in (sr_res.data or []):
        key = (str(r.get("scorer_player_id") or ""), r.get("scorer_name") or "", (r.get("scorer_team") or "").strip())
        existing_scorers[key] = bool(r.get("did_score"))
except Exception:
    pass

# =====================
# Group tipovaní střelci
# =====================
scorer_groups = {}
for p in preds:
    sname = (p.get("scorer_name") or "").strip()
    if not sname:
        continue
    team = (p.get("scorer_team") or "").strip()
    pid = str(p.get("scorer_player_id") or "")
    key = (pid, sname, team)
    if key not in scorer_groups:
        scorer_groups[key] = []
    scorer_groups[key].append(p)

st.markdown("---")
st.subheader("⚽ Tipovaní střelci (admin rozhodne: dal / nedal)")

scorer_state = {}
if not scorer_groups:
    st.info("Nikdo zatím netipoval střelce u tohoto zápasu.")
else:
    # hezčí: ukáž taky kdo to tipoval
    for key, plist in scorer_groups.items():
        pid, name, team = key
        prev = existing_scorers.get(key, False)
        count = len(plist)

        with st.expander(f"{name} ({team}) — tipů: {count}", expanded=True):
            scorer_state[key] = st.checkbox(
                "✅ Dal gól v tomto zápase",
                value=prev,
                key=f"sc_{match_id}_{pid}_{name}_{team}",
            )
            st.caption("Kdo ho tipoval:")
            for p in plist:
                email = user_emails.get(p["user_id"], p["user_id"])
                st.write(f"- {email} (tip: {int(p.get('home_score') or 0)}:{int(p.get('away_score') or 0)})")

# =====================
# Preview points
# =====================
st.markdown("---")
st.subheader("🧾 Náhled bodů po uložení")

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

    preview_rows.append(
        {
            "Uživatel": email,
            "Tip": f"{ph}:{pa}",
            "Střelec": sname or "—",
            "Body": pts,
            "Původně": old_pts,
            "Δ": pts - old_pts,
            "Detail": str(detail),
        }
    )

if preview_rows:
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)
else:
    st.info("Zatím nikdo netipoval výsledek pro tento zápas.")

# =====================
# SAVE + RESET (ADMIN)
# =====================
with c3:
    # ---- ULOŽIT VÝSLEDEK + PŘEPOČET ----
    if st.button("💾 Uložit výsledek + přepočítat body", type="primary"):
        with st.spinner("Ukládám výsledek a přepočítávám body..."):
            errors = []
            success_steps = []
            
            try:
                now = datetime.now(timezone.utc).isoformat()

                # 1) ulož výsledek do matches
                try:
                    supabase.table("matches").update(
                        {
                            "final_home_score": int(final_home),
                            "final_away_score": int(final_away),
                            "evaluated_at": now,
                        }
                    ).eq("id", match_id).execute()
                    success_steps.append("✅ Výsledek zápasu uložen")
                except Exception as e:
                    errors.append(f"❌ Chyba při ukládání výsledku zápasu: {e}")

                # 2) scorer_results: smaž staré a vlož nové (jen pro tipované střelce)
                try:
                    supabase.table("scorer_results").delete().eq("match_id", match_id).execute()
                    success_steps.append("✅ Staré záznamy střelců smazány")
                except Exception as e:
                    errors.append(f"⚠️ Varování při mazání starých střelců: {e}")

                scorer_payload = []
                for key, did in scorer_state.items():
                    pid, name, team = key
                    scorer_payload.append(
                        {
                            "match_id": match_id,  # BIGINT
                            "scorer_player_id": pid if pid else None,  # uuid nebo None
                            "scorer_name": name,
                            "scorer_team": team or None,
                            "did_score": bool(did),
                        }
                    )

                if scorer_payload:
                    try:
                        supabase.table("scorer_results").insert(scorer_payload).execute()
                        success_steps.append(f"✅ Uloženo {len(scorer_payload)} záznamů střelců")
                    except Exception as e:
                        errors.append(f"❌ Chyba při ukládání střelců: {e}")

                # 3) přepočet bodů + update predictions
                updated_preds = 0
                failed_preds = 0
                
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

                        # update predictions
                        supabase.table("predictions").update(
                            {
                                "points_awarded": int(new_pts),
                                "evaluated_at": now,
                                "points_detail": detail,
                            }
                        ).eq("user_id", p["user_id"]).eq("match_id", match_id).execute()
                        
                        updated_preds += 1
                        
                    except Exception as e:
                        failed_preds += 1
                        email = user_emails.get(p.get("user_id"), "unknown")
                        errors.append(f"⚠️ Chyba při ukládání tipu pro {email}: {e}")

                if updated_preds > 0:
                    success_steps.append(f"✅ Aktualizováno {updated_preds} tipů")
                if failed_preds > 0:
                    errors.append(f"⚠️ Selhalo {failed_preds} tipů")

                # 4) Zobraz výsledky
                st.markdown("### 📊 Výsledek operace")
                
                for step in success_steps:
                    st.success(step)
                
                for error in errors:
                    st.error(error)
                
                if not errors:
                    st.balloons()
                    st.success("🎉 Vše proběhlo v pořádku!")
                    st.info("💡 Tip: Nyní běž na Leaderboard a klikni na 'Synchronizace bodů' pro přepočet celkových bodů všech hráčů.")
                    
                    if st.button("➡️ Přejít na Synchronizaci bodů"):
                        st.switch_page("pages/5_Admin_Sync_Points.py")
                else:
                    st.warning("⚠️ Operace proběhla s chybami. Zkontroluj výše uvedené chyby.")

            except Exception as e:
                st.error(f"❌ Kritická chyba: {e}")
                import traceback
                st.code(traceback.format_exc())

    # ---- SMAZAT HODNOCENÍ (RESET) ----
    st.markdown("---")
    is_evaluated = (m.get("final_home_score") is not None) or (m.get("final_away_score") is not None) or (m.get("evaluated_at") is not None)

    with st.expander("🗑️ Reset / smazání hodnocení zápasu", expanded=False):
        st.caption(
            "Toto smaže výsledek zápasu, vymaže záznamy střelců, vynuluje body u všech tipů pro tento zápas "
            "a správně odečte body z profiles.points."
        )

        confirm_reset = st.checkbox(
            "⚠️ Rozumím tomu a chci smazat hodnocení (vrátit zápas do stavu 'nevyhodnocený')",
            key=f"confirm_reset_{match_id}"
        )

        if st.button(
            "🗑️ Smazat hodnocení zápasu",
            type="secondary",
            disabled=(not confirm_reset) or (not is_evaluated and not preds),
            key=f"btn_reset_{match_id}"
        ):
            try:
                # 1) načti aktuální body v predictions (kvůli odečtu z profiles)
                preds_with_points = (
                    supabase.table("predictions")
                    .select("user_id, points_awarded")
                    .eq("match_id", match_id)
                    .execute()
                ).data or []

                delta_by_user = {}
                for p in preds_with_points:
                    uid = p.get("user_id")
                    pts = int(p.get("points_awarded") or 0)
                    if uid and pts != 0:
                        # chceme odečíst, takže delta je záporná
                        delta_by_user[uid] = delta_by_user.get(uid, 0) - pts

                # 2) reset zápasu v matches
                supabase.table("matches").update(
                    {
                        "final_home_score": None,
                        "final_away_score": None,
                        "evaluated_at": None,
                    }
                ).eq("id", match_id).execute()

                # 3) reset predictions pro tento zápas
                #    (Body = 0, detail & evaluated_at smažeme)
                supabase.table("predictions").update(
                    {
                        "points_awarded": 0,
                        "points_detail": None,
                        "evaluated_at": None,
                    }
                ).eq("match_id", match_id).execute()

                # 4) smaž scorer_results pro tento zápas
                supabase.table("scorer_results").delete().eq("match_id", match_id).execute()

                # 5) odečti body z profiles.points
                if delta_by_user:
                    uids = list(delta_by_user.keys())
                    profs = (
                        supabase.table("profiles")
                        .select("user_id, points")
                        .in_("user_id", uids)
                        .execute()
                    ).data or []

                    current = {r["user_id"]: int(r.get("points") or 0) for r in profs}

                    for uid, delta in delta_by_user.items():
                        new_total = current.get(uid, 0) + int(delta)
                        # pojistka proti záporným bodům
                        supabase.table("profiles").update(
                            {"points": max(new_total, 0)}
                        ).eq("user_id", uid).execute()

                st.success("🗑️ Hodnocení zápasu bylo smazáno. Zápas je zpět jako 'nevyhodnocený'.")
                st.rerun()

            except Exception as e:
                st.error(f"Chyba při mazání hodnocení: {e}")