import random

# ── Kártya konstansok ─────────────────────────────────────────────────────────

SUITS = ["piros", "zöld", "makk", "tök"]
RANKS = ["7", "8", "9", "alsó", "felső", "király", "10", "ász"]
RANK_VALUES = {r: i for i, r in enumerate(RANKS)}   # 7=0 … ász=7

SUIT_EMOJI  = {"piros": "🔴", "zöld": "🍀", "makk": "🌰", "tök": "🔔"}
SUIT_NAMES  = {"piros": "Piros", "zöld": "Zöld", "makk": "Makk", "tök": "Tök"}
RANK_LABEL  = {
    "7": "7", "8": "8", "9": "9",
    "alsó": "Alsó", "felső": "Felső", "király": "Király",
    "10": "10", "ász": "Ász",
}

TRUMP_SUIT = "piros"   # Piros az adu

# Az ulti-hoz kapcsolódó speciális lapok
ULTI_CARD  = "makk_ász"          # ulti: utolsó ütést ezzel kell nyerni
PASSZ_CARD = "makk_ász"          # passz: mindet megnyerni


# ── Kártya helpers ────────────────────────────────────────────────────────────

def make_card(suit: str, rank: str) -> str:
    return f"{suit}_{rank}"


def parse_card(card: str):
    """Visszaadja (suit, rank) tuple-t."""
    idx = card.index("_")
    return card[:idx], card[idx + 1:]


def card_label(card: str) -> str:
    suit, rank = parse_card(card)
    return f"{SUIT_EMOJI[suit]} {RANK_LABEL[rank]}"


def suit_label(suit: str) -> str:
    return f"{SUIT_EMOJI[suit]} {SUIT_NAMES[suit]}"


def all_cards():
    return [make_card(s, r) for s in SUITS for r in RANKS]   # 32 lap


def sorted_hand(hand):
    """Rendezi a kezet szín, majd érték szerint."""
    def key(c):
        suit, rank = parse_card(c)
        return (SUITS.index(suit), RANK_VALUES[rank])
    return sorted(hand, key=key)


# ── Osztás ────────────────────────────────────────────────────────────────────

def deal() -> dict:
    """
    Visszaad {seat_str -> lapok} dict-et.
    Az első licitáló (0-ás ülőhely) kap 12 lapot, a többi 10-et.
    """
    deck = all_cards()
    random.shuffle(deck)
    # Véletlenszerű első licitáló (0, 1 vagy 2)
    first_bidder = random.randint(0, 2)
    seats = list(range(3))
    seats.remove(first_bidder)
    return {
        str(first_bidder): deck[:12],
        str(seats[0]):      deck[12:22],
        str(seats[1]):      deck[22:32],
        "_first_bidder":    first_bidder,
    }


# ── Ütés logika ───────────────────────────────────────────────────────────────

def card_beats(card_a: str, card_b: str, lead_suit: str) -> bool:
    """Igaz, ha card_a veri card_b-t, figyelembe véve az adut és a vezető színt."""
    suit_a, rank_a = parse_card(card_a)
    suit_b, rank_b = parse_card(card_b)

    if suit_a == TRUMP_SUIT and suit_b != TRUMP_SUIT:
        return True
    if suit_b == TRUMP_SUIT and suit_a != TRUMP_SUIT:
        return False
    if suit_a == suit_b:
        return RANK_VALUES[rank_a] > RANK_VALUES[rank_b]
    # Különböző, nem adu szín: a vezető szín veri az idegen színt
    return suit_a == lead_suit


def trick_winner_seat(trick: list, lead_suit: str) -> int:
    """
    trick: [{seat: int, card: str}, ...]
    Visszaadja a nyerő ülőhelyet.
    """
    best = trick[0]
    for play in trick[1:]:
        if card_beats(play["card"], best["card"], lead_suit):
            best = play
    return best["seat"]


def get_legal_cards(hand: list, current_trick: list, lead_suit) -> list:
    """
    Visszaadja a játszható lapok listáját.
    Szabályok: színkényszer, ütéskényszer, adukényszer.
    """
    if not lead_suit:
        return list(hand)   # Vezet: bármit játszhat

    # Melyik lap nyeri most az ütést?
    winning_card = None
    if current_trick:
        win_seat = trick_winner_seat(current_trick, lead_suit)
        winning_card = next(p["card"] for p in current_trick if p["seat"] == win_seat)

    # 1. Színkényszer: van-e a vezető színből?
    suit_cards = [c for c in hand if parse_card(c)[0] == lead_suit]
    if suit_cards:
        # Ütéskényszer: ha tud ütni, köteles ütni
        if winning_card:
            winning_suit = [c for c in suit_cards if card_beats(c, winning_card, lead_suit)]
            if winning_suit:
                return winning_suit
        return suit_cards

    # 2. Adukényszer: nincs vezető szín → adut kell játszani ha van
    trump_cards = [c for c in hand if parse_card(c)[0] == TRUMP_SUIT]
    if trump_cards:
        # Ütéskényszer adunál is
        if winning_card:
            winning_trump = [c for c in trump_cards if card_beats(c, winning_card, lead_suit)]
            if winning_trump:
                return winning_trump
        return trump_cards

    # 3. Sem vezető szín, sem adu → bármi
    return list(hand)


# ── Automatikus ütés-kiértékelés ──────────────────────────────────────────────

def eval_passz(completed_tricks: list, szolista_seat: int) -> bool:
    """Igaz, ha a szólista mind a 10 ütést megnyerte."""
    return all(t["winner"] == szolista_seat for t in completed_tricks)


def eval_ulti(completed_tricks: list, szolista_seat: int) -> bool:
    """Igaz, ha a szólista az utolsó ütést makk ásszal nyerte."""
    if len(completed_tricks) < 10:
        return False
    last = completed_tricks[-1]
    if last["winner"] != szolista_seat:
        return False
    szolista_card = next(
        p["card"] for p in last["cards"] if p["seat"] == szolista_seat
    )
    return szolista_card == ULTI_CARD


def eval_betli(completed_tricks: list, szolista_seat: int) -> bool:
    """Igaz, ha a szólista egyetlen ütést sem nyert."""
    return all(t["winner"] != szolista_seat for t in completed_tricks)


def eval_negyasz(completed_tricks: list, szolista_seat: int) -> bool:
    """Igaz, ha a szólista mind a 4 ászt begyűjtötte."""
    aces = {f"{s}_ász" for s in SUITS}
    szolista_cards = set()
    for t in completed_tricks:
        if t["winner"] == szolista_seat:
            for p in t["cards"]:
                szolista_cards.add(p["card"])
    return aces.issubset(szolista_cards)


def auto_evaluate(bid_name: str, completed_tricks: list, szolista_seat: int) -> list | None:
    """
    Megpróbál automatikusan kiértékelni egyes liciteket.
    None jelenti: nem tudja automatikusan → manuális kell.
    """
    from modules.scoring import BIDS
    components = BIDS[bid_name]["components"]
    results = []
    for comp in components:
        name = comp["name"]
        if name == "Passz":
            results.append(eval_passz(completed_tricks, szolista_seat))
        elif name == "Piros passz":
            results.append(eval_passz(completed_tricks, szolista_seat))
        elif name == "Ulti":
            results.append(eval_ulti(completed_tricks, szolista_seat))
        elif name == "Piros ulti":
            results.append(eval_ulti(completed_tricks, szolista_seat))
        elif name in ("Betli", "Piros betli", "Terített betli", "Terített rebetli"):
            results.append(eval_betli(completed_tricks, szolista_seat))
        elif name == "Négyász":
            results.append(eval_negyasz(completed_tricks, szolista_seat))
        else:
            return None   # Nem tudja automatikusan
    return results
