BIDS = {
    "Passz":                          {"components": [{"name": "Passz",                          "figure": 1}]},
    "Piros passz":                    {"components": [{"name": "Piros passz",                    "figure": 2}]},
    "Negyvenszáz":                    {"components": [{"name": "Negyvenszáz",                    "figure": 4}]},
    "Négyász":                        {"components": [{"name": "Négyász",                        "figure": 4}]},
    "Ulti":                           {"components": [{"name": "Ulti",                           "figure": 4},
                                                      {"name": "Passz",                          "figure": 1}]},
    "Betli":                          {"components": [{"name": "Betli",                          "figure": 5}]},
    "Durchmars":                      {"components": [{"name": "Durchmars",                      "figure": 6}]},
    "Negyvenszáz-négyász":            {"components": [{"name": "Negyvenszáz",                    "figure": 4},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Negyvenszáz-ulti":               {"components": [{"name": "Negyvenszáz",                    "figure": 4},
                                                      {"name": "Ulti",                           "figure": 4}]},
    "Ulti-négyász":                   {"components": [{"name": "Ulti",                           "figure": 4},
                                                      {"name": "Négyász",                        "figure": 4},
                                                      {"name": "Passz",                          "figure": 1}]},
    "Húszszáz":                       {"components": [{"name": "Húszszáz",                       "figure": 8}]},
    "Piros ulti":                     {"components": [{"name": "Piros ulti",                     "figure": 8},
                                                      {"name": "Piros passz",                    "figure": 2}]},
    "Piros betli":                    {"components": [{"name": "Piros betli",                    "figure": 10}]},
    "Negyvenszáz-ulti-négyász":       {"components": [{"name": "Negyvenszáz",                    "figure": 4},
                                                      {"name": "Ulti",                           "figure": 4},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Húszzáz-négyász":                {"components": [{"name": "Húszzáz",                        "figure": 8},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Húszzáz-ulti":                   {"components": [{"name": "Húszzáz",                        "figure": 8},
                                                      {"name": "Ulti",                           "figure": 4}]},
    "Piros ulti-négyász":             {"components": [{"name": "Piros ulti",                     "figure": 8},
                                                      {"name": "Négyász",                        "figure": 4},
                                                      {"name": "Piros passz",                    "figure": 2}]},
    "Piros húszszáz":                 {"components": [{"name": "Piros húszszáz",                 "figure": 16}]},
    "Húszzáz-ulti-négyász":           {"components": [{"name": "Húszzáz",                        "figure": 8},
                                                      {"name": "Ulti",                           "figure": 4},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Piros negyvenszáz-ulti":         {"components": [{"name": "Piros negyvenszáz",              "figure": 8},
                                                      {"name": "Ulti",                           "figure": 8}]},
    "Piros húszszáz-négyász":         {"components": [{"name": "Piros húszszáz",                 "figure": 16},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Piros negyvenszáz-ulti-négyász": {"components": [{"name": "Piros negyvenszáz",              "figure": 8},
                                                      {"name": "Ulti",                           "figure": 8},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Terített betli":                 {"components": [{"name": "Terített betli",                 "figure": 20}]},
    "Piros húszszáz-ulti":            {"components": [{"name": "Piros húszszáz",                 "figure": 16},
                                                      {"name": "Ulti",                           "figure": 8}]},
    "Terített durchmars":             {"components": [{"name": "Terített durchmars",             "figure": 24}]},
    "Terített rebetli":               {"components": [{"name": "Terített rebetli",               "figure": 25}]},
    "Piros húszszáz-ulti-négyász":    {"components": [{"name": "Piros húszszáz",                 "figure": 16},
                                                      {"name": "Ulti",                           "figure": 8},
                                                      {"name": "Négyász",                        "figure": 4}]},
    "Terített redurchmars":           {"components": [{"name": "Terített redurchmars",           "figure": 30}]},
}

KONTRA_LEVELS = {
    "Nincs":      1,
    "Kontra":     2,
    "Rekontra":   4,
    "Szubkontra": 8,
}

BID_NAMES = list(BIDS.keys())


def get_total_figure(bid_name, component_kontrak=None):
    comps = BIDS[bid_name]["components"]
    if component_kontrak is None:
        return sum(c["figure"] for c in comps)
    return sum(c["figure"] * component_kontrak[i] for i, c in enumerate(comps))


def calculate_round_points(szolista_idx, bid_name, component_kontrak, component_results):
    """
    component_kontrak:  list[int]  – kontra szorzó komponensenként (1/2/4/8)
    component_results:  list[bool] – sikerült-e komponensenként
    Visszaad: {0: pont, 1: pont, 2: pont}
    Szólista nyeréskor: +2*figura, fogók: -figura (és fordítva bukáskor)
    """
    points = {0: 0, 1: 0, 2: 0}
    fogok = [i for i in range(3) if i != szolista_idx]

    for i, comp in enumerate(BIDS[bid_name]["components"]):
        fig = comp["figure"] * component_kontrak[i]
        if component_results[i]:
            points[szolista_idx] += 2 * fig
            for f in fogok:
                points[f] -= fig
        else:
            points[szolista_idx] -= 2 * fig
            for f in fogok:
                points[f] += fig

    return points
