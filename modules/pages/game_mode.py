import streamlit as st
from datetime import datetime, timezone
from modules.scoring import BIDS, KONTRA_LEVELS, BID_NAMES, calculate_round_points, get_total_figure
from modules.db import save_game


# ── Session state inicializálás ───────────────────────────────────────────────

def _init():
    defaults = {
        "gm_step": "setup",
        "gm_players": ["", "", ""],
        "gm_forint_alap": 10,
        "gm_scores": {0: 0, 1: 0, 2: 0},
        "gm_rounds": [],
        "gm_cr_szolista": 0,
        "gm_cr_bid": BID_NAMES[0],
        "gm_cr_component_kontrak": [1],
        "gm_cr_component_kontra_labels": ["Nincs"],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Segédfüggvények ───────────────────────────────────────────────────────────

def _score_row(players, scores, forint_alap):
    cols = st.columns(3)
    for i, col in enumerate(cols):
        pts = scores[i]
        sign = "+" if pts > 0 else ""
        ft = pts * forint_alap
        ft_sign = "+" if ft > 0 else ""
        col.metric(
            label=players[i],
            value=f"{sign}{pts} pont",
            delta=f"{ft_sign}{ft} Ft" if forint_alap > 0 else None,
        )


def _kontra_suffix(component_kontra_labels):
    parts = [l for l in component_kontra_labels if l != "Nincs"]
    return f" [{', '.join(parts)}]" if parts else ""


def _reset_game():
    for k in list(st.session_state.keys()):
        if k.startswith("gm_"):
            del st.session_state[k]


# ── Lépések renderelése ───────────────────────────────────────────────────────

def _render_setup():
    st.subheader("Játékosok és beállítások")

    c1, c2, c3 = st.columns(3)
    p1 = c1.text_input("1. játékos", key="gm_setup_p1")
    p2 = c2.text_input("2. játékos", key="gm_setup_p2")
    p3 = c3.text_input("3. játékos", key="gm_setup_p3")

    forint_alap = st.number_input(
        "Alapét (Ft/pont)", min_value=0, value=10, step=5, key="gm_setup_forint",
        help="0 = csak pontozás, forint számítás nélkül"
    )

    if st.button("🎮 Játék kezdése", type="primary", use_container_width=True):
        names = [p1.strip(), p2.strip(), p3.strip()]
        if not all(names):
            st.error("Add meg mindhárom játékos nevét!")
            return
        if len(set(n.lower() for n in names)) < 3:
            st.error("A három név nem egyezhet meg!")
            return
        st.session_state.gm_players = names
        st.session_state.gm_forint_alap = forint_alap
        st.session_state.gm_scores = {0: 0, 1: 0, 2: 0}
        st.session_state.gm_rounds = []
        st.session_state.gm_step = "round_bid"
        st.rerun()


def _render_round_bid():
    players = st.session_state.gm_players
    scores = st.session_state.gm_scores
    forint_alap = st.session_state.gm_forint_alap
    rounds = st.session_state.gm_rounds

    _score_row(players, scores, forint_alap)

    if rounds:
        last = rounds[-1]
        pts = last["points"]
        parts = []
        for i in range(3):
            p = pts[i]
            s = "+" if p > 0 else ""
            parts.append(f"{players[i]}: {s}{p}")
        suffix = _kontra_suffix(last.get("component_kontra_labels", []))
        st.caption(f"Előző kör – {last['szolista_name']} / {last['bid']}{suffix} → {'  |  '.join(parts)}")

    st.divider()
    st.subheader(f"Kör #{len(rounds) + 1} – Licit")

    szolista_name = st.radio("Ki játszik?", players, horizontal=True, key="gm_bid_szolista_radio")
    szolista_idx = players.index(szolista_name)

    bid_name = st.selectbox("Licit", BID_NAMES, key="gm_bid_name_select")
    components = BIDS[bid_name]["components"]

    # Per-komponens kontra
    st.write("**Kontra:**")
    component_kontrak = []
    component_kontra_labels = []

    for i, comp in enumerate(components):
        label = st.radio(
            f"{comp['name']}  ({comp['figure']} pont)",
            list(KONTRA_LEVELS.keys()),
            horizontal=True,
            key=f"gm_bid_kontra_{i}",
        )
        mult = KONTRA_LEVELS[label]
        component_kontrak.append(mult)
        component_kontra_labels.append(label)

    # Összesített info
    eff_fig = sum(comp["figure"] * component_kontrak[i] for i, comp in enumerate(components))
    base_fig = sum(c["figure"] for c in components)
    if eff_fig != base_fig:
        st.caption(f"Összfigura: {base_fig} → kontrakkal: **{eff_fig}**  |  Szólista: ±{2*eff_fig}, fogók: ∓{eff_fig}")
    else:
        st.caption(f"Összfigura: {base_fig}  |  Szólista: ±{2*base_fig}, fogók: ∓{base_fig}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Eredmény rögzítése →", type="primary", use_container_width=True):
            st.session_state.gm_cr_szolista = szolista_idx
            st.session_state.gm_cr_bid = bid_name
            st.session_state.gm_cr_component_kontrak = component_kontrak
            st.session_state.gm_cr_component_kontra_labels = component_kontra_labels
            st.session_state.gm_step = "round_result"
            st.rerun()
    with col2:
        if st.button("🏁 Játék vége", use_container_width=True):
            st.session_state.gm_step = "finished"
            st.rerun()

    if rounds:
        with st.expander(f"Körök naplója ({len(rounds)} kör)"):
            for j, r in enumerate(rounds, 1):
                pts = r["points"]
                pts_str = "  ".join(
                    f"{players[i]}: {'+' if pts[i]>0 else ''}{pts[i]}" for i in range(3)
                )
                suffix = _kontra_suffix(r.get("component_kontra_labels", []))
                st.write(f"**{j}.** {r['szolista_name']} – {r['bid']}{suffix} → {pts_str}")


def _render_round_result():
    players = st.session_state.gm_players
    szolista_idx = st.session_state.gm_cr_szolista
    bid_name = st.session_state.gm_cr_bid
    component_kontrak = st.session_state.gm_cr_component_kontrak
    component_kontra_labels = st.session_state.gm_cr_component_kontra_labels

    st.subheader("Eredmény rögzítése")

    suffix = _kontra_suffix(component_kontra_labels)
    st.info(f"**{players[szolista_idx]}** játszik  ·  **{bid_name}**{suffix}")

    components = BIDS[bid_name]["components"]
    results = []

    for i, comp in enumerate(components):
        mult = component_kontrak[i]
        fig_eff = comp["figure"] * mult
        kontra_str = f" × {mult} = **{fig_eff}**" if mult > 1 else f" = **{fig_eff}**"
        label_str = f"**{comp['name']}** – {comp['figure']}{kontra_str} pont"
        if component_kontra_labels[i] != "Nincs":
            label_str += f"  _{component_kontra_labels[i]}_"
        st.markdown(label_str)

        success = st.radio(
            "Eredmény",
            ["✅ Sikerült", "❌ Nem sikerült"],
            key=f"gm_res_{i}",
            horizontal=True,
            label_visibility="collapsed",
        )
        results.append(success == "✅ Sikerült")
        if i < len(components) - 1:
            st.write("")

    points = calculate_round_points(szolista_idx, bid_name, component_kontrak, results)

    st.divider()
    st.write("**Várható pontok:**")
    cols = st.columns(3)
    for i, col in enumerate(cols):
        pts = points[i]
        col.metric(players[i], f"{'+' if pts>0 else ''}{pts}")

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Vissza", use_container_width=True):
            st.session_state.gm_step = "round_bid"
            st.rerun()
    with col2:
        if st.button("✅ Rögzítés", type="primary", use_container_width=True):
            round_data = {
                "szolista": szolista_idx,
                "szolista_name": players[szolista_idx],
                "bid": bid_name,
                "component_kontrak": component_kontrak,
                "component_kontra_labels": component_kontra_labels,
                "components": [
                    {**comp, "success": results[j], "kontra": component_kontrak[j]}
                    for j, comp in enumerate(components)
                ],
                "points": points,
            }
            st.session_state.gm_rounds.append(round_data)
            for i in range(3):
                st.session_state.gm_scores[i] += points[i]
            for i in range(len(components)):
                st.session_state.pop(f"gm_res_{i}", None)
            st.session_state.gm_step = "round_bid"
            st.rerun()


def _render_finished(db):
    players = st.session_state.gm_players
    scores = st.session_state.gm_scores
    forint_alap = st.session_state.gm_forint_alap
    rounds = st.session_state.gm_rounds

    st.subheader("🏁 Játék vége – Végeredmény")
    _score_row(players, scores, forint_alap)

    st.divider()
    st.write("**Forint elszámolás:**")
    for i in range(3):
        pts = scores[i]
        ft = pts * forint_alap
        sign_p = "+" if pts > 0 else ""
        sign_f = "+" if ft > 0 else ""
        emoji = "🟢" if pts > 0 else "🔴" if pts < 0 else "⚪"
        st.write(f"{emoji} **{players[i]}**: {sign_p}{pts} pont"
                 + (f"  =  **{sign_f}{ft} Ft**" if forint_alap > 0 else ""))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Mentés Firebase-be", type="primary", use_container_width=True):
            game_data = {
                "mode": "game",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "players": players,
                "forint_alap": forint_alap,
                "final_scores": [scores[i] for i in range(3)],
                "rounds": [
                    {**r, "points": [r["points"][i] for i in range(3)]}
                    for r in rounds
                ],
            }
            doc_id, err = save_game(db, game_data)
            if err:
                st.error(f"Mentési hiba: {err}")
            else:
                st.success(f"Elmentve! (ID: {doc_id})")
    with col2:
        if st.button("🎮 Új játék", use_container_width=True):
            _reset_game()
            st.rerun()

    if rounds:
        with st.expander(f"Összes kör ({len(rounds)})"):
            for j, r in enumerate(rounds, 1):
                pts = r["points"]
                pts_str = "  ".join(
                    f"{players[i]}: {'+' if pts[i]>0 else ''}{pts[i]}" for i in range(3)
                )
                suffix = _kontra_suffix(r.get("component_kontra_labels", []))
                st.write(f"**{j}.** {r['szolista_name']} – {r['bid']}{suffix} → {pts_str}")


# ── Belépőpont ────────────────────────────────────────────────────────────────

def render_game_mode(db):
    _init()
    step = st.session_state.gm_step

    if step == "setup":
        _render_setup()
    elif step == "round_bid":
        _render_round_bid()
    elif step == "round_result":
        _render_round_result()
    elif step == "finished":
        _render_finished(db)
