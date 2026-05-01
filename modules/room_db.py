"""
Firestore szoba-kezelés az online multiplayer játékhoz.
Szoba státuszok: waiting → bidding → discarding → playing → evaluating → finished
"""
import random
import string
import uuid
from datetime import datetime, timezone

ROOMS = "ulti_rooms"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase, k=6))


def _gen_pid() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ref(db, room_id: str):
    return db.collection(ROOMS).document(room_id.upper())


# ── Szoba CRUD ────────────────────────────────────────────────────────────────

def get_room(db, room_id: str) -> dict | None:
    doc = _ref(db, room_id).get()
    if doc.exists:
        d = doc.to_dict()
        d["id"] = doc.id
        return d
    return None


def create_room(db, name: str, forint_alap: int):
    """Szoba létrehozása. Visszaad (room_code, player_id)."""
    code = _gen_code()
    pid = _gen_pid()
    _ref(db, code).set({
        "status": "waiting",
        "forint_alap": forint_alap,
        "created_at": _now(),
        "players": [{"name": name, "player_id": pid, "seat": 0}],
        "hands": {},
        "first_bidder_seat": None,
        "bidding": {},
        "szolista_seat": None,
        "bid_name": None,
        "component_kontrak": [],
        "discarding": {},
        "gameplay": {},
        "result": {},
    })
    return code, pid


def join_room(db, room_id: str, name: str):
    """Csatlakozás szobához. Visszaad (player_id, hiba_str)."""
    rid = room_id.strip().upper()
    room = get_room(db, rid)
    if room is None:
        return None, "Nem létező szobakód."
    if room["status"] != "waiting":
        return None, "A játék már elkezdődött."
    players = room.get("players", [])
    if len(players) >= 3:
        return None, "A szoba tele van (3/3)."
    # Duplikált név ellenőrzés
    if any(p["name"].lower() == name.strip().lower() for p in players):
        return None, "Ez a név már foglalt ebben a szobában."
    pid = _gen_pid()
    seat = len(players)
    players.append({"name": name.strip(), "player_id": pid, "seat": seat})
    _ref(db, rid).update({"players": players})
    return pid, None


def start_game(db, room_id: str):
    """Kártyák osztása, játék indítása."""
    from modules.cards import deal
    hands_raw = deal()
    first_bidder = hands_raw.pop("_first_bidder")
    _ref(db, room_id).update({
        "status": "bidding",
        "hands": hands_raw,
        "first_bidder_seat": first_bidder,
        "bidding": {
            "current_seat": first_bidder,
            "current_bid_name": None,
            "current_bid_seat": None,
            "consecutive_passes": 0,
            "must_bid": True,          # az első licitálónak kötelező licitálni
            "history": [],
        },
    })


# ── Licit fázis ───────────────────────────────────────────────────────────────

def do_bid(db, room_id: str, room: dict, seat: int, bid_name: str):
    """Ülőhely licitet mond."""
    bidding = room["bidding"]
    history = list(bidding.get("history", []))
    history.append({"seat": seat, "action": "bid", "bid_name": bid_name})
    next_seat = (seat + 1) % 3
    _ref(db, room_id).update({
        "bidding.current_bid_name": bid_name,
        "bidding.current_bid_seat": seat,
        "bidding.consecutive_passes": 0,
        "bidding.must_bid": False,
        "bidding.history": history,
        "bidding.current_seat": next_seat,
    })


def do_pass(db, room_id: str, room: dict, seat: int):
    """Ülőhely passzol."""
    bidding = room["bidding"]
    history = list(bidding.get("history", []))
    history.append({"seat": seat, "action": "pass"})
    consecutive = bidding.get("consecutive_passes", 0) + 1
    next_seat = (seat + 1) % 3

    updates = {
        "bidding.consecutive_passes": consecutive,
        "bidding.must_bid": False,
        "bidding.history": history,
        "bidding.current_seat": next_seat,
    }

    # 3 egymás utáni passz → licit vége
    if consecutive >= 3:
        szolista_seat = bidding.get("current_bid_seat", room.get("first_bidder_seat", 0))
        bid_name = bidding.get("current_bid_name")
        hands = {k: list(v) for k, v in room.get("hands", {}).items()}
        first_bidder = room.get("first_bidder_seat", 0)

        # Ha a szólista nem az eredeti 12-lapos → kapja meg a 2 extra lapot
        if szolista_seat != first_bidder:
            fb_hand = list(hands.get(str(first_bidder), []))
            sz_hand = list(hands.get(str(szolista_seat), []))
            extra = fb_hand[10:]              # a 2 extra lap
            hands[str(first_bidder)] = fb_hand[:10]
            hands[str(szolista_seat)] = sz_hand + extra

        from modules.scoring import BIDS
        n_comps = len(BIDS[bid_name]["components"]) if bid_name else 0

        updates.update({
            "szolista_seat": szolista_seat,
            "bid_name": bid_name,
            "component_kontrak": [1] * n_comps,
            "hands": hands,
            "status": "discarding",
            "discarding": {"done": False, "discarded": []},
        })

    _ref(db, room_id).update(updates)


# ── Dobás fázis ───────────────────────────────────────────────────────────────

def do_discard(db, room_id: str, room: dict, cards_to_discard: list):
    """Szólista eldob 2 lapot."""
    szolista = room["szolista_seat"]
    hand = list(room["hands"].get(str(szolista), []))
    for c in cards_to_discard:
        if c in hand:
            hand.remove(c)
    _ref(db, room_id).update({
        f"hands.{szolista}": hand,
        "discarding.done": True,
        "discarding.discarded": list(cards_to_discard),
        "status": "playing",
        "gameplay": {
            "current_player": room["szolista_seat"],    # szólista kezd
            "lead_suit": None,
            "current_trick": [],
            "tricks_won": [0, 0, 0],
            "completed_tricks": [],
            "renounce_seat": None,
            "trick_number": 0,
        },
    })


# ── Játék fázis ───────────────────────────────────────────────────────────────

def do_play_card(db, room_id: str, room: dict, seat: int, card: str):
    """Ülőhely lerak egy lapot."""
    from modules.cards import trick_winner_seat, parse_card

    hands   = {k: list(v) for k, v in room["hands"].items()}
    gp      = room["gameplay"]
    hand    = list(hands.get(str(seat), []))
    current_trick    = list(gp.get("current_trick", []))
    lead_suit        = gp.get("lead_suit")
    tricks_won       = list(gp.get("tricks_won", [0, 0, 0]))
    completed_tricks = list(gp.get("completed_tricks", []))
    trick_number     = gp.get("trick_number", 0)

    if card in hand:
        hand.remove(card)

    # Vezető szín beállítása az első lapnál
    if not current_trick:
        lead_suit = parse_card(card)[0]

    current_trick.append({"seat": seat, "card": card})

    updates = {
        f"hands.{seat}": hand,
        "gameplay.current_trick": current_trick,
        "gameplay.lead_suit": lead_suit,
    }

    if len(current_trick) == 3:
        # Ütés befejezve
        winner = trick_winner_seat(current_trick, lead_suit)
        tricks_won[winner] += 1
        completed_tricks.append({
            "winner": winner,
            "cards": list(current_trick),
            "lead_suit": lead_suit,
        })
        trick_number += 1

        updates.update({
            "gameplay.tricks_won": tricks_won,
            "gameplay.completed_tricks": completed_tricks,
            "gameplay.current_trick": [],
            "gameplay.lead_suit": None,
            "gameplay.current_player": winner,
            "gameplay.trick_number": trick_number,
        })

        if trick_number == 10:
            # Minden ütés lejátszva → kiértékelés
            _try_auto_evaluate(updates, room, completed_tricks, tricks_won)
    else:
        # Következő játékos az ütésben (az óra járásával)
        lead_seat = current_trick[0]["seat"]
        played = {p["seat"] for p in current_trick}
        for d in range(1, 3):
            candidate = (lead_seat + d) % 3
            if candidate not in played:
                updates["gameplay.current_player"] = candidate
                break

    _ref(db, room_id).update(updates)


def _try_auto_evaluate(updates: dict, room: dict, completed_tricks: list, tricks_won: list):
    """Megpróbál automatikusan kiértékelni; ha nem sikerül, 'evaluating' státuszra lép."""
    from modules.cards import auto_evaluate
    from modules.scoring import BIDS, calculate_round_points

    bid_name     = room.get("bid_name")
    szolista     = room.get("szolista_seat")
    kontrak      = room.get("component_kontrak", [1])
    forint_alap  = room.get("forint_alap", 0)

    auto_results = auto_evaluate(bid_name, completed_tricks, szolista)

    if auto_results is not None:
        points = calculate_round_points(szolista, bid_name, kontrak, auto_results)
        updates["status"] = "finished"
        updates["result"] = {
            "szolista_seat": szolista,
            "bid_name": bid_name,
            "component_results": auto_results,
            "tricks_won": tricks_won,
            "points": [points[i] for i in range(3)],
            "forint_alap": forint_alap,
            "auto_evaluated": True,
        }
    else:
        # Manuális kiértékelés kell
        updates["status"] = "evaluating"
        updates["result"] = {
            "szolista_seat": szolista,
            "bid_name": bid_name,
            "tricks_won": tricks_won,
            "forint_alap": forint_alap,
            "auto_evaluated": False,
        }


def do_evaluate(db, room_id: str, room: dict, component_results: list):
    """Manuális kiértékelés (szólista erősíti meg)."""
    from modules.scoring import calculate_round_points

    szolista    = room["szolista_seat"]
    bid_name    = room["bid_name"]
    kontrak     = room.get("component_kontrak", [1])
    forint_alap = room.get("forint_alap", 0)
    tricks_won  = room.get("result", {}).get("tricks_won", [0, 0, 0])

    points = calculate_round_points(szolista, bid_name, kontrak, component_results)
    _ref(db, room_id).update({
        "status": "finished",
        "result.component_results": component_results,
        "result.points": [points[i] for i in range(3)],
        "result.forint_alap": forint_alap,
        "result.tricks_won": tricks_won,
    })


def reset_room(db, room_id: str):
    """Szoba törlése (új játék előtt)."""
    _ref(db, room_id).delete()
