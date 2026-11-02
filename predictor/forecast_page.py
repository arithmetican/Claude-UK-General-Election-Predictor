"""GB forecast page with switchable model options.

Usage:
    python -m predictor.forecast_page

Writes output/forecast_2024.json and .html. The base model is uniform swing,
measured separately for England, Scotland and Wales, using the mean of the
per-seat changes. Each option below can be switched independently on the
page; every combination is computed here in advance.

Options (each independent of the others):
    transfer  uniform (base) or proportional: a party losing ground keeps a fixed
              fraction of its previous share; a party gaining wins a fixed
              fraction of the vote it previously lacked (the theta method)
    average   mean (base) or median of the per-seat changes
    conlab, conlib, lablib
              off (base) or on: in England, Con v Lab / Con v LibDem /
              Lab v LibDem seats (by the 2019 top two parties) get their own
              swing once 5 of them have declared
"""

import itertools
import json
import logging

from .forecast import CountryModel, Swing, ThetaSwing
from .replay import ROOT, load_baseline, load_live, replay

OUT = ROOT / "output" / "forecast_2024"
TEMPLATE = ROOT / "web" / "forecast_template.html"

OFF_ON = [{"value": "off", "label": "Off"}, {"value": "on", "label": "On"}]
# Each option: name, label, and its values; the first value is the base model.
OPTIONS = [
    {"name": "transfer", "label": "Swing",
     "values": [{"value": "uniform", "label": "Uniform"}, {"value": "proportional", "label": "Proportional"}]},
    {"name": "average", "label": "Average",
     "values": [{"value": "mean", "label": "Mean"}, {"value": "median", "label": "Median"}]},
    {"name": "conlab", "label": "Con v Lab", "values": OFF_ON},
    {"name": "conlib", "label": "Con v LibDem", "values": OFF_ON},
    {"name": "lablib", "label": "Lab v LibDem", "values": OFF_ON},
]
TYPE_OPTIONS = {"conlab": "Con v Lab", "conlib": "Con v LibDem", "lablib": "Lab v LibDem"}


def make_model(choice):
    """The forecast object for one combination of option values."""
    stat = choice["average"]
    base = (lambda: ThetaSwing(stat)) if choice["transfer"] == "proportional" else (lambda: Swing(stat))
    types = [t for opt, t in TYPE_OPTIONS.items() if choice.get(opt) == "on"]
    return lambda: CountryModel(base, types)


def method_for(choice):
    """Which replay method's labels and number formats to use."""
    return "theta" if choice["transfer"] == "proportional" else "uniform"


def describe(choice):
    if choice["transfer"] == "proportional":
        how = (f"proportional swing (the {choice['average']} θ: parties losing ground keep a fixed "
               "fraction of their vote, parties gaining win a fixed fraction of the vote they lacked)")
    else:
        how = f"uniform swing (the {choice['average']} change in vote share)"
    types = [t for opt, t in TYPE_OPTIONS.items() if choice.get(opt) == "on"]
    split = (" In England, " + ", ".join(types) + " seats each have their own swing once 5 of them "
             "have declared.") if types else ""
    return (f"Great Britain seats won plus seats predicted by {how}, measured separately in "
            f"England, Scotland and Wales, after each declaration.{split}")


def build(baseline_seats, live_results):
    """Every combination, stored compactly: the step details shared by all
    variants once, and for each variant only its seat totals and swings."""
    names = [o["name"] for o in OPTIONS]
    shared, variants = None, {}
    for values in itertools.product(*[[v["value"] for v in o["values"]] for o in OPTIONS]):
        choice = dict(zip(names, values))
        key = "&".join(f"{n}={choice[n]}" for n in names)
        r = replay(baseline_seats, live_results, method_for(choice), make=make_model(choice))
        parties = r["parties"]
        countries = list(r["steps"][0]["swing"])
        if shared is None:
            shared = {k: v for k, v in r.items() if k not in ("steps", "method", "description",
                                                              "swing_label", "swing_decimals")}
            shared.update(title="UK general election, July 2024: forecast",
                          baseline="UKDecember2019.json", live="UKJuly2024.json",
                          countries=countries,
                          steps=[{k: s[k] for k in ("n", "seat", "live_name", "winner", "declared_by_country")}
                                 for s in r["steps"]])
        swing_parties = {c: list(r["steps"][0]["swing"][c]) for c in countries}
        variants[key] = {
            "method": r["method"], "description": describe(choice), "average": choice["average"],
            "swing_label": r["swing_label"], "swing_decimals": r["swing_decimals"],
            "swing_parties": swing_parties,
            "seats": [[s["seats"][p] for p in parties] for s in r["steps"]],
            "swing": [[[s["swing"][c][p] for p in swing_parties[c]] for c in countries] for s in r["steps"]],
        }
    return {"options": OPTIONS, "shared": shared, "variants": variants}


def expand(data, key):
    """One variant in the full form the page draws (also used by the tests)."""
    sh, v = data["shared"], data["variants"][key]
    steps = []
    for i, m in enumerate(sh["steps"]):
        s = dict(m)
        s["seats"] = dict(zip(sh["parties"], v["seats"][i]))
        s["swing"] = {c: dict(zip(v["swing_parties"][c], v["swing"][i][j]))
                      for j, c in enumerate(sh["countries"])}
        steps.append(s)
    r = {k: x for k, x in sh.items() if k != "steps"}
    r.update({k: x for k, x in v.items() if k not in ("seats", "swing", "swing_parties")})
    r["steps"] = steps
    return r


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    _, baseline_seats = load_baseline(ROOT / "data" / "UKDecember2019.json")
    data = build(baseline_seats, load_live(ROOT / "data" / "UKJuly2024.json"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.with_suffix(".json").write_text(text + "\n", encoding="utf-8")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*RESULTS*/null", text.replace("</", "<\\/"))
    OUT.with_suffix(".html").write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.with_suffix('.json')} and .html ({len(data['variants'])} variants, "
          f"{len(text) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
