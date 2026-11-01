"""GB forecast page with switchable model options.

Usage:
    python -m predictor.forecast_page

Writes output/forecast_2024.json and .html. The base model is uniform swing,
measured separately for England, Scotland and Wales, using the mean of the
per-seat changes. Each option below can be switched independently on the
page; every combination is computed here in advance.

Options so far:
    average   mean (base) or median of the per-seat changes
"""

import itertools
import json
import logging

from .forecast import SwingByCountry
from .replay import ROOT, load_baseline, load_live, replay

OUT = ROOT / "output" / "forecast_2024"
TEMPLATE = ROOT / "web" / "forecast_template.html"

# Each option: name, label, and its values; the first value is the base model.
OPTIONS = [
    {"name": "average", "label": "Average",
     "values": [{"value": "mean", "label": "Mean"}, {"value": "median", "label": "Median"}]},
]


def make_model(choice):
    """The forecast object for one combination of option values."""
    return lambda: SwingByCountry(choice["average"])


def describe(choice):
    return ("Great Britain seats won plus seats predicted by uniform swing (the "
            f"{choice['average']} change in vote share, measured separately in England, "
            "Scotland and Wales), after each declaration.")


def build(baseline_seats, live_results):
    variants = {}
    names = [o["name"] for o in OPTIONS]
    for values in itertools.product(*[[v["value"] for v in o["values"]] for o in OPTIONS]):
        choice = dict(zip(names, values))
        key = "&".join(f"{n}={choice[n]}" for n in names)
        r = replay(baseline_seats, live_results, "uniform", make=make_model(choice))
        r.update(title="UK general election, July 2024: forecast",
                 description=describe(choice), average=choice["average"],
                 baseline="UKDecember2019.json", live="UKJuly2024.json")
        variants[key] = r
    return {"options": OPTIONS, "variants": variants}


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    _, baseline_seats = load_baseline(ROOT / "data" / "UKDecember2019.json")
    data = build(baseline_seats, load_live(ROOT / "data" / "UKJuly2024.json"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")
    page = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*RESULTS*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    OUT.with_suffix(".html").write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.with_suffix('.json')} and .html ({len(data['variants'])} variants)")


if __name__ == "__main__":
    main()
