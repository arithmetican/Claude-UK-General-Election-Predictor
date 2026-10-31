"""Scatter of each party's previous vote share against its change, per seat.

Usage:
    python -m predictor.scatter
    python -m predictor.scatter --baseline data/UKDecember2019.json \\
        --live data/UKJuly2024.json --out output/scatter_2024

Writes <out>.json (the points) and <out>.html (the graph).

One point per party per declared Great Britain seat, for parties that
stood there at either election. Northern Ireland is left out.
"""

import argparse
import json
import logging
from pathlib import Path

from .matching import ConstituencyMatcher
from .parties import GB_PARTIES, read_votes, vote_shares
from .replay import ROOT, load_baseline, load_live

TEMPLATE = ROOT / "web" / "scatter_template.html"


def scatter_points(baseline_seats, live_results):
    matcher = ConstituencyMatcher(baseline_seats)
    points, seen = [], set()
    for order, (live_name, live_votes) in enumerate(live_results, start=1):
        seat = matcher.match(live_name)
        if seat is None or seat in seen:
            continue
        info = baseline_seats[seat]
        if info["country"] == "Northern Ireland":
            continue
        votes, _ = read_votes(live_votes)
        new = vote_shares(votes)
        if new is None:
            continue
        seen.add(seat)
        old = info["shares"]
        for p in GB_PARTIES:
            if old[p] > 0 or new[p] > 0:
                points.append({
                    "seat": seat, "country": info["country"], "region": info["region"],
                    "order": order, "party": p,
                    "old": round(100 * old[p], 2), "new": round(100 * new[p], 2),
                })
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--baseline", default=ROOT / "data" / "UKDecember2019.json")
    parser.add_argument("--live", default=ROOT / "data" / "UKJuly2024.json")
    parser.add_argument("--title", default="Change in vote share against previous share, 2019 to 2024")
    parser.add_argument("--out", default=ROOT / "output" / "scatter_2024")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    _, baseline_seats = load_baseline(args.baseline)
    results = {
        "title": args.title,
        "baseline": Path(args.baseline).name,
        "live": Path(args.live).name,
        "parties": list(GB_PARTIES),
        "points": scatter_points(baseline_seats, load_live(args.live)),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
        f.write("\n")
    data = json.dumps(results, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*RESULTS*/null", data)
    out.with_suffix(".html").write_text(page, encoding="utf-8")
    print(f"{len(results['points'])} points; wrote {out.with_suffix('.json')} and .html")


if __name__ == "__main__":
    main()
