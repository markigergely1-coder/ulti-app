"""
Online multiplayer játékmód.
Státuszok: waiting → bidding → discarding → playing → evaluating → finished
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from modules.cards import (
    card_label, suit_label, sorted_hand, get_legal_cards,
    SUITS, TRUMP_SUIT, parse_card,
)
from modules.room_db import (
    get_room, create_room, join_room, start_game,
    do_bid, do_pass, do_discard, do_play_card, do_evaluate, reset_room,
)
from modules.scoring import BIDS, BID_NAMES


# ── Session state ─────────────────────────────────────────────────────────────

def _init():
    for k, v in [
        ("og_room_id",    None),
        ("og_player_id",  None),
        ("og_player_name", ""),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v


def _my_seat(room: dict) -> int | None:
    pid = st.session_state.og_player_id
    for p in room.get("players", []):
        if p["player_id"] == pid:
            return p["seat"]
    return None


def _player_name(room: dict, seat: int) -> str:
    for p in room.get("players", []):
        if p["seat"] == seat:
            return p["name"]
    return f"#{seat}"


def _leave():
    st.session_state.og_room_id   = None
    st.session_state.og_player_id = None


# ── Segéd UI ──────────────────────────────────────────────────────────────────

def _show_players(room: dict, my_seat: int):
    players = sorted(room.get("players", []), key=lambda p: p["seat"])
    cols = st.columns(len(players))
    for i, p in enumerate(players):
        icon = "🟢" if p["seat"] == my_seat else "👤"
        label = f"{icon} {p['name']}"
        if p["seat"] == room.get("first_bidder_seat"):
            label += " *(12 lap)*"
        cols[i].markdown(f"**{label}**")


def _show_scores_header(room: dict, my_seat: int):
    result = room.get("result", {})
    points = result.get("points")
    forint = result.get("forint_alap", room.get("forint_alap", 0))
    if not points:
        return
    cols = st.columns(3)
    for i, col in enumerate(cols):
        name = _player_name(room, i)
        pts = points[i]
        s = "+" if pts > 0 else ""
        ft = pts * forint
        fs = "+" if ft > 0 else ""
        col.metric(
            f"{'👑 ' if i == my_seat else ''}{name}",
            f"{s}{pts} pont",
            f"{fs}{ft} Ft" if forint > 0 else None,
        )


def _show_hand(hand: list, legal: list | None = None, title: str = "Kezed"):
    """Lapok megjelenítése szín szerint csoportosítva."""
    st.write(f"**{title}:**")
    for suit in SUITS:
        suit_cards = [c for c in sorted_hand(hand) if parse_card(c)[0] == suit]
        if not suit_cards:
            continue
        labels = []
        for c in suit_cards:
            lbl = card_label(c)
            if legal is not None:
                if c not in legal:
                    lbl = f"~~{lbl}~~"
            labels.append(lbl)
        st.markdown(f"{suit_label(suit)}: {' &nbsp; '.join(labels)}", unsafe_allow_html=True)


def _show_current_trick(room: dict):
    gp = room.get("gameplay", {})
    trick = gp.get("current_trick", [])
    if not trick:
        return
    st.write("**Aktuális ütés:**")
    lead_suit = gp.get("lead_suit")
    cols = st.columns(len(trick))
    for i, play in enumerate(trick):
        name = _player_name(room, play["seat"])
        lead_marker = " *(vezet)*" if i == 0 else ""
        cols[i].markdown(f"{name}{lead_marker}  \n**{card_label(play['card'])}**")


def _show_trick_counts(room: dict):
    gp = room.get("gameplay", {})
    tw = gp.get("tricks_won", [0, 0, 0])
    szolista = room.get("szolista_seat")
    cols = st.columns(3)
    for i, col in enumerate(cols):
        name = _player_name(room, i)
        role = " *(szólista)*" if i == szolista else ""
        col.metric(f"{name}{role}", f"{tw[i]} ütés")


def _bid_history(room: dict):
    bidding = room.get("bidding", {})
    history = bidding.get("history", [])
    if not history:
        return
    with st.expander("Licit napló"):
        for h in history:
            name = _player_name(room, h["seat"])
            if h["action"] == "bid":
                st.write(f"✅ **{name}**: {h['bid_name']}")
            else:
                st.write(f"❌ **{name}**: passz")


# ── Fázisok ───────────────────────────────────────────────────────────────────

def _render_lobby(db):
    st.subheader("Online játék")
    tab_new, tab_join = st.tabs(["➕ Új szoba", "🚪 Csatlakozás"])

    with tab_new:
        name = st.text_input("Neved", key="og_new_name")
        forint = st.number_input("Alapét (Ft/pont)", min_value=0, value=10, step=5, key="og_new_ft")
        if st.button("Szoba létrehozása", type="primary", use_container_width=True):
            if not name.strip():
                st.error("Add meg a neved!")
                return
            code, pid = create_room(db, name.strip(), forint)
            st.session_state.og_room_id   = code
            st.session_state.og_player_id = pid
            st.session_state.og_player_name = name.strip()
            st.rerun()

    with tab_join:
        code_in = st.text_input("Szobakód (6 betű)", max_chars=6, key="og_join_code")
        name_in = st.text_input("Neved", key="og_join_name")
        if st.button("Csatlakozás", type="primary", use_container_width=True):
            if not code_in.strip() or not name_in.strip():
                st.error("Add meg a szobakódot és a neved!")
                return
            pid, err = join_room(db, code_in.strip(), name_in.strip())
            if err:
                st.error(err)
            else:
                st.session_state.og_room_id   = code_in.strip().upper()
                st.session_state.og_player_id = pid
                st.session_state.og_player_name = name_in.strip()
                st.rerun()


def _render_waiting(db, room: dict, my_seat: int):
    st_autorefresh(interval=3000, key="wait_refresh")

    players = room.get("players", [])
    code = room["id"]

    st.subheader("⏳ Várakozás a játékosokra")
    st.info(f"Szobakód: **{code}** — oszd meg a barátaiddal!")

    _show_players(room, my_seat)
    st.caption(f"{len(players)}/3 játékos csatlakozott")

    if len(players) == 3:
        if my_seat == 0:   # a házigazda indítja
            st.success("Mindenki megérkezett!")
            if st.button("🎮 Játék indítása", type="primary", use_container_width=True):
                start_game(db, code)
                st.rerun()
        else:
            st.success("Mindenki megérkezett — a házigazda indítja a játékot...")

    if st.button("Kilépés", use_container_width=True):
        _leave()
        st.rerun()


def _render_bidding(db, room: dict, my_seat: int):
    bidding = room.get("bidding", {})
    current_seat   = bidding.get("current_seat")
    current_bid    = bidding.get("current_bid_name")
    must_bid       = bidding.get("must_bid", False)
    my_turn        = (current_seat == my_seat)

    if not my_turn:
        st_autorefresh(interval=2500, key="bid_wait_refresh")

    st.subheader("🎯 Licitálás")
    _show_players(room, my_seat)

    # Jelenlegi licit
    if current_bid:
        bidder_name = _player_name(room, bidding.get("current_bid_seat"))
        st.info(f"Jelenlegi licit: **{current_bid}** — {bidder_name}")
    else:
        st.info("Még nincs licit.")

    # Kézben lévő lapok
    hand = room.get("hands", {}).get(str(my_seat), [])
    _show_hand(hand)

    _bid_history(room)
    st.divider()

    if my_turn:
        st.write(f"**A te köröd!**")

        # Elérhető licetek (csak a jelenleginél magasabb)
        if current_bid is None:
            available = BID_NAMES
        else:
            idx = BID_NAMES.index(current_bid)
            available = BID_NAMES[idx + 1:]

        selected_bid = st.selectbox("Licit:", available, key="og_bid_select")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Licet mond", type="primary", use_container_width=True):
                do_bid(db, room["id"], room, my_seat, selected_bid)
                st.rerun()
        with col2:
            # Az első körben (must_bid=True) nem lehet passzolni
            if must_bid:
                st.button("❌ Passz", disabled=True, use_container_width=True,
                          help="Az első licitálónak kötelező licitet mondani.")
            else:
                if st.button("❌ Passz", use_container_width=True):
                    do_pass(db, room["id"], room, my_seat)
                    st.rerun()
    else:
        current_name = _player_name(room, current_seat)
        st.info(f"⏳ {current_name} licitál...")

    if st.button("Kilépés", use_container_width=True):
        _leave()
        st.rerun()


def _render_discarding(db, room: dict, my_seat: int):
    szolista = room.get("szolista_seat")
    bid_name = room.get("bid_name")

    if my_seat != szolista:
        st_autorefresh(interval=2500, key="disc_wait_refresh")
        szolista_name = _player_name(room, szolista)
        st.subheader("⏳ Dobás fázis")
        st.info(f"**{szolista_name}** dob 2 lapot ({bid_name}). Várakozás...")
        return

    hand = room.get("hands", {}).get(str(my_seat), [])
    st.subheader("🗑️ Dobás fázis")
    st.info(f"Licit: **{bid_name}** — válassz ki 2 lapot amelyeket ledob!")

    _show_hand(hand)
    st.write("")

    card_options = sorted_hand(hand)
    selected = st.multiselect(
        "2 lapot dobj el:",
        options=card_options,
        format_func=card_label,
        key="og_discard_select",
    )

    if len(selected) == 2:
        if st.button("🗑️ Eldobás", type="primary", use_container_width=True):
            do_discard(db, room["id"], room, selected)
            st.rerun()
    else:
        st.caption(f"Pontosan 2 lapot válassz ({len(selected)}/2 kijelölve).")


def _render_playing(db, room: dict, my_seat: int):
    gp          = room.get("gameplay", {})
    cur_player  = gp.get("current_player")
    current_trick = gp.get("current_trick", [])
    lead_suit   = gp.get("lead_suit")
    my_turn     = (cur_player == my_seat)

    if not my_turn:
        st_autorefresh(interval=2000, key="play_wait_refresh")

    szolista    = room.get("szolista_seat")
    bid_name    = room.get("bid_name")
    trick_num   = gp.get("trick_number", 0)

    st.subheader(f"🃏 Játék — {trick_num + 1}. ütés")
    st.caption(f"Licit: **{bid_name}** | Szólista: **{_player_name(room, szolista)}** | Adu: {suit_label(TRUMP_SUIT)}")

    _show_trick_counts(room)
    st.divider()
    _show_current_trick(room)

    hand  = room.get("hands", {}).get(str(my_seat), [])
    legal = get_legal_cards(hand, current_trick, lead_suit)
    _show_hand(hand, legal=legal)

    st.divider()
    if my_turn:
        st.write("**A te köröd — melyik lapot rakod le?**")

        if lead_suit and legal != list(hand):
            keny = []
            if any(parse_card(c)[0] == lead_suit for c in legal):
                keny.append("színkényszer")
            elif any(parse_card(c)[0] == TRUMP_SUIT for c in legal):
                keny.append("adukényszer")
            if keny:
                st.warning(f"⚠️ {', '.join(keny).capitalize()} és ütéskényszer érvényes!")

        selected_card = st.selectbox(
            "Lap:",
            legal,
            format_func=card_label,
            key="og_play_select",
        )
        if st.button("▶ Lerak", type="primary", use_container_width=True):
            do_play_card(db, room["id"], room, my_seat, selected_card)
            st.rerun()
    else:
        cur_name = _player_name(room, cur_player)
        st.info(f"⏳ {cur_name} következik...")

    # Befejezett ütések (összenyitható)
    completed = gp.get("completed_tricks", [])
    if completed:
        with st.expander(f"Befejezett ütések ({len(completed)})"):
            for i, t in enumerate(reversed(completed), 1):
                winner_name = _player_name(room, t["winner"])
                cards_str = "  ".join(card_label(p["card"]) for p in t["cards"])
                st.write(f"**{len(completed)-i+1}.** ütés → **{winner_name}** nyeri | {cards_str}")


def _render_evaluating(db, room: dict, my_seat: int):
    """Manuális kiértékelés — a szólista erősíti meg."""
    szolista  = room.get("szolista_seat")
    bid_name  = room.get("bid_name")
    result    = room.get("result", {})
    gp_done   = room.get("gameplay", {})
    completed = gp_done.get("completed_tricks", [])
    tw        = result.get("tricks_won", [0, 0, 0])

    if my_seat != szolista:
        st_autorefresh(interval=2500, key="eval_wait_refresh")
        st.subheader("⏳ Kiértékelés")
        _show_trick_counts({"gameplay": {"tricks_won": tw},
                            "szolista_seat": szolista,
                            "players": room["players"]})
        st.info(f"**{_player_name(room, szolista)}** erősíti meg az eredményt...")
        return

    st.subheader("📊 Eredmény megerősítése")
    st.write(f"Licit: **{bid_name}**")

    cols = st.columns(3)
    for i, col in enumerate(cols):
        emoji = "🟢" if i == szolista else "🔵"
        col.metric(f"{emoji} {_player_name(room, i)}", f"{tw[i]} ütés")

    # Befejezett ütések
    with st.expander("Ütések részletei"):
        for i, t in enumerate(completed, 1):
            winner_name = _player_name(room, t["winner"])
            cards_str = "  ".join(card_label(p["card"]) for p in t["cards"])
            st.write(f"**{i}.** {winner_name} | {cards_str}")

    st.divider()
    components = BIDS[bid_name]["components"]
    results = []
    st.write("**Sikerült-e az egyes bemondások?**")
    for i, comp in enumerate(components):
        success = st.radio(
            f"**{comp['name']}** ({comp['figure']} pont)",
            ["✅ Sikerült", "❌ Nem sikerült"],
            horizontal=True,
            key=f"og_eval_{i}",
        )
        results.append(success == "✅ Sikerült")

    if st.button("✅ Eredmény rögzítése", type="primary", use_container_width=True):
        do_evaluate(db, room["id"], room, results)
        st.rerun()


def _render_finished(db, room: dict, my_seat: int):
    result   = room.get("result", {})
    points   = result.get("points", [0, 0, 0])
    forint   = result.get("forint_alap", room.get("forint_alap", 0))
    bid_name = result.get("bid_name", room.get("bid_name", ""))
    szolista = result.get("szolista_seat", room.get("szolista_seat"))
    comp_res = result.get("component_results", [])
    tw       = result.get("tricks_won", [0, 0, 0])

    st.subheader("🏁 Játék vége!")
    st.caption(f"Licit: **{bid_name}** — Szólista: **{_player_name(room, szolista)}**")

    # Eredmény
    cols = st.columns(3)
    for i, col in enumerate(cols):
        name = _player_name(room, i)
        pts  = points[i]
        ft   = pts * forint
        sp   = "+" if pts > 0 else ""
        fp   = "+" if ft > 0 else ""
        em   = "🟢" if pts > 0 else "🔴" if pts < 0 else "⚪"
        col.metric(
            f"{em} {name}",
            f"{sp}{pts} pont",
            f"{fp}{ft} Ft" if forint > 0 else None,
        )

    # Komponens eredmény
    if comp_res and bid_name:
        st.divider()
        st.write("**Bemondások:**")
        comps = BIDS[bid_name]["components"]
        for i, comp in enumerate(comps):
            icon = "✅" if comp_res[i] else "❌"
            st.write(f"{icon} {comp['name']} ({comp['figure']} pont)")

    # Ütések
    st.divider()
    st.write("**Ütések:**")
    tcols = st.columns(3)
    for i, col in enumerate(tcols):
        col.metric(_player_name(room, i), f"{tw[i]} ütés")

    st.divider()
    if st.button("🎮 Új szoba (kilépés)", use_container_width=True):
        _leave()
        st.rerun()


# ── Belépőpont ────────────────────────────────────────────────────────────────

def render_online_game(db):
    _init()

    if db is None:
        st.error("⚠️ Nincs Firebase kapcsolat. Ellenőrizd a secrets.toml-t.")
        return

    room_id   = st.session_state.og_room_id
    player_id = st.session_state.og_player_id

    # Lobby
    if room_id is None or player_id is None:
        _render_lobby(db)
        return

    # Szoba betöltése
    room = get_room(db, room_id)
    if room is None:
        st.error("A szoba nem található. Lehet, hogy törölték.")
        _leave()
        return

    my_seat = _my_seat(room)
    if my_seat is None:
        st.error("Nem vagy ebben a szobában.")
        _leave()
        return

    # Szoba fejléc
    st.caption(f"Szoba: **{room_id}**  |  Te: **{_player_name(room, my_seat)}** (#{my_seat})")

    status = room.get("status", "waiting")

    if status == "waiting":
        _render_waiting(db, room, my_seat)
    elif status == "bidding":
        _render_bidding(db, room, my_seat)
    elif status == "discarding":
        _render_discarding(db, room, my_seat)
    elif status == "playing":
        _render_playing(db, room, my_seat)
    elif status == "evaluating":
        _render_evaluating(db, room, my_seat)
    elif status == "finished":
        _render_finished(db, room, my_seat)
    else:
        st.warning(f"Ismeretlen játékstátusz: {status}")
