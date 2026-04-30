# Minden licit komponensekre bontva. Ha egy licitnek több komponense van
# (pl. Ulti + Passz), azok egymástól függetlenül sikerülhetnek/bukhatnak.

BIDS = {
    "Passz":                          {"components": [{"name": "Passz",                          "figure": 1}]},
    "Piros passz":                    {"components": [{"name": "Piros passz",                    "figure": 2}]},
    "Negyvenszáz":                    {"components": [{"name": "Negyvenszáz",                    "figure": 4}]},
    "Négyász":                        {"components": [{"name": "Négyász",                        "figure": 4}]},
    "Ulti":                           {"components": [{"name": "Ulti",                           "figure": 4},
                                                      {"name": "Passz",                          "figure": 1}]},
    "Betli":                          {"components": [{"name": "Betli",                          "figure": 5}]},
    "Durthmars":                      {"components": [{"name": "Durthmars",                      "figure": 6}]},
    "Negyvenszáz-négyász":            {"components": [{"name": "Negyvenszáz-négyász",            "figure": 8}]},
    "Negyvenszáz-ulti":               {"components": [{"name": "Negyvenszáz-ulti",               "figure": 8}]},
    "Ulti-négyász":                   {"components": [{"name": "Ulti-négyász",                   "figure": 8},
                                                      {"name": "Passz",                          "figure": 1}]},
    "Húszszáz":                       {"components": [{"name": "Húszszáz",                       "figure": 8}]},
    "Piros ulti":                     {"components": [{"name": "Piros ulti",                     "figure": 8},
                                                      {"name": "Piros passz",                    "figure": 2}]},
    "Piros betli":                    {"components": [{"name": "Piros betli",                    "figure": 10}]},
    "Negyvenszáz-ulti-négyász":       {"components": [{"name": "Negyvenszáz-ulti-négyász",       "figure": 12}]},
    "Húszzáz-négyász":                {"components": [{"name": "Húszzáz-négyász",                "figure": 12}]},
    "Húszzáz-ulti":                   {"components": [{"name": "Húszzáz-ulti",                   "figure": 12}]},
    "Piros ulti-négyász":             {"components": [{"name": "Piros ulti-négyász",             "figure": 12},
                                                      {"name": "Piros passz",                    "figure": 2}]},
    "Piros húszszáz":                 {"components": [{"name": "Piros húszszáz",                 "figure": 16}]},
    "Húszzáz-ulti-négyász":           {"components": [{"name": "Húszzáz-ulti-négyász",           "figure": 16}]},
    "Piros negyvenszáz-ulti":         {"components": [{"name": "Piros negyvenszáz-ulti",         "figure": 16}]},
    "Piros húszszáz-négyász":         {"components": [{"name": "Piros húszszáz-négyász",         "figure": 20}]},
    "Piros negyvenszáz-ulti-négyász": {"components": [{"name": "Piros negyvenszáz-ulti-négyász", "figure": 20}]},
    "Terített betli":                 {"components": [{"name": "Terített betli",                 "figure": 20}]},
    "Piros húszszáz-ulti":            {"components": [{"name": "Piros húszszáz-ulti",            "figure": 24}]},
    "Terített durthmars":             {"components": [{"name": "Terített durthmars",             "figure": 24}]},
    "Terített re betli":              {"components": [{"name": "Terített re betli",              "figure": 25}]},
    "Piros húszszáz-ulti-négyász":    {"components": [{"name": "Piros húszszáz-ulti-négyász",    "figure": 28}]},
    "Terített re durthmars":          {"components": [{"name": "Terített re durthmars",          "figure": 30}]},
}

KONTRA_LEVELS = {
    "Nincs":      1,
    "Kontra":     2,
    "Rekontra":   4,
    "Szubkontra": 8,
}

BID_NAMES = list(BIDS.keys())


def get_total_figure(bid_name):
    return sum(c["figure"] for c in BIDS[bid_name]["components"])


def calculate_round_points(szolista_idx, bid_name, kontra_mult, component_results):
    """
    component_results: list[bool] – egy elem per komponens (True = sikerült)
    Visszaad: {0: pont, 1: pont, 2: pont}
    Szólista nyeréskor: +2*figura, fogók: -figura
    Szólista bukáskor:  -2*figura, fogók: +figura
    """
    points = {0: 0, 1: 0, 2: 0}
    fogok = [i for i in range(3) if i != szolista_idx]

    for i, comp in enumerate(BIDS[bid_name]["components"]):
        fig = comp["figure"] * kontra_mult
        if component_results[i]:
            points[szolista_idx] += 2 * fig
            for f in fogok:
                points[f] -= fig
        else:
            points[szolista_idx] -= 2 * fig
            for f in fogok:
                points[f] += fig

    return points
