"""Replay an election in declaration order and forecast after each result.

Usage:
    python -m predictor.replay
    python -m predictor.replay --baseline data/UKDecember2019.json \\
        --live data/UKJuly2024.json --out output/replay_2024

Writes <out>.json (the numbers) and <out>.html (the graph).

Methods (--method):
    uniform  average change in share, per country (default; output/replay_2024)
    theta    proportional for losers, complement for gainers, one theta per
             party per country (output/replay_2024_theta)

After n Great Britain declarations, each party's total is:
    seats it actually won among the n declared seats
  + seats it is predicted to win among the 632 - n undeclared GB seats.
Northern Ireland seats are skipped: they are not used in the forecast and
not drawn on the graph, but still count towards the 650 seats in the House.
"""

import argparse
import json
import logging
from pathlib import Path

from .forecast import SwingByCountry, ThetaByCountry
from .matching import ConstituencyMatcher
from .parties import GB_PARTIES, INDEPENDENT, read_votes, vote_shares

log = logging.getLogger(__name__)

TOTAL_SEATS = 650
MAJORITY = TOTAL_SEATS // 2 + 1
GRAPH_PARTIES = GB_PARTIES[:-1] + (INDEPENDENT, GB_PARTIES[-1])  # Others last

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "web" / "graph_template.html"


def load_baseline(path):
    """Previous election: {seat name: {"country":..., "region":..., "shares":...}}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    seats = {}
    for s in data["constituencies"]:
        seats[s["constituency"]] = {
            "country": s["country"],
            "region": s["region"],
            "shares": vote_shares(s["votes"]),
        }
    gb = [n for n, s in seats.items() if s["country"] != "Northern Ireland"]
    for name in gb:
        if seats[name]["shares"] is None:
            raise ValueError(f"Baseline seat {name!r} has no votes")
    return data, seats


def load_live(path):
    """Live results in declaration order: [(seat name, {party: votes})]."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.items())


def totals(declared, predicted):
    counts = dict.fromkeys(GRAPH_PARTIES, 0)
    for party in list(declared.values()) + list(predicted.values()):
        counts[party] = counts.get(party, 0) + 1
    return counts


METHODS = {
    "uniform": {
        "make": SwingByCountry,
        "out": "replay_2024",
        "description": "Great Britain seats won plus seats predicted by swing (measured separately "
                       "in England, Scotland and Wales), after each declaration.",
        "swing_label": "Swing", "swing_scale": 100, "swing_decimals": 1, "round": 2,
    },
    "theta": {
        "make": ThetaByCountry,
        "out": "replay_2024_theta",
        "description": "Great Britain seats won plus seats predicted by the theta method "
                       "(proportional for parties losing ground, proportional on the non-vote for "
                       "parties gaining; one theta per party, measured separately in England, "
                       "Scotland and Wales), after each declaration.",
        "swing_label": "θ", "swing_scale": 1, "swing_decimals": 3, "round": 4,
    },
}


def replay(baseline_seats, live_results, method="uniform", make=None):
    """Run the forecast after every GB declaration. Returns a results dict."""
    spec = METHODS[method]
    matcher = ConstituencyMatcher(baseline_seats)
    gb_seats = [n for n, s in baseline_seats.items() if s["country"] != "Northern Ireland"]
    swing = (make or spec["make"])()
    declared = {}          # seat -> actual winner
    ni_declared = {}       # NI seat -> live party name of winner
    skipped = []           # declarations we could not use

    def predicted():
        return {
            seat: swing.predict(baseline_seats[seat]["shares"], baseline_seats[seat]["country"])
            for seat in gb_seats if seat not in declared
        }

    def step(seat=None, live_name=None, winner=None):
        return {
            "n": len(declared),
            "seat": seat,
            "live_name": live_name,
            "winner": winner,
            "seats": totals(declared, predicted()),
            "swing": {c: {p: round(spec["swing_scale"] * v, spec["round"]) for p, v in ch.items()}
                      for c, ch in swing.changes().items()},
            "declared_by_country": swing.declared(),
        }

    steps = []  # one entry per GB declaration, starting at n = 1
    for live_name, live_votes in live_results:
        seat = matcher.match(live_name)
        if seat is None:
            skipped.append({"live_name": live_name, "reason": matcher.unmatched.get(
                live_name if isinstance(live_name, str) else repr(live_name))})
            continue
        if baseline_seats[seat]["country"] == "Northern Ireland":
            if isinstance(live_votes, dict) and live_votes:
                ni_declared[seat] = max(live_votes, key=lambda p: _int(live_votes[p]))
            continue
        if seat in declared:
            log.warning("Seat %r declared twice; keeping the first result", seat)
            skipped.append({"live_name": live_name, "reason": "declared twice"})
            continue
        votes, winner = read_votes(live_votes)
        new_shares = vote_shares(votes)
        if new_shares is None or winner is None:
            log.warning("No usable votes for %r; skipped", live_name)
            skipped.append({"live_name": live_name, "reason": "no usable votes"})
            continue
        swing.add(baseline_seats[seat]["country"], baseline_seats[seat]["shares"], new_shares)
        declared[seat] = winner
        steps.append(step(seat, live_name, winner))

    return {
        "total_seats": TOTAL_SEATS,
        "majority": MAJORITY,
        "gb_seats": len(gb_seats),
        "ni_seats": len(baseline_seats) - len(gb_seats),
        "ni_declared": ni_declared,
        "parties": list(GRAPH_PARTIES),
        "method": method,
        "description": spec["description"],
        "swing_label": spec["swing_label"],
        "swing_decimals": spec["swing_decimals"],
        "steps": steps,
        "skipped": skipped,
    }


def _int(value):
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return -1


def write_outputs(results, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
        f.write("\n")
    # Embed the results in the page so it opens straight from the file.
    data = json.dumps(results, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*RESULTS*/null", data)
    out.with_suffix(".html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--baseline", default=ROOT / "data" / "UKDecember2019.json")
    parser.add_argument("--live", default=ROOT / "data" / "UKJuly2024.json")
    parser.add_argument("--title", default="UK general election, July 2024 (replay)")
    parser.add_argument("--method", choices=sorted(METHODS), default="uniform")
    parser.add_argument("--out", default=None,
                        help="output path without extension (default depends on --method)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    _, baseline_seats = load_baseline(args.baseline)
    if args.out is None:
        args.out = ROOT / "output" / METHODS[args.method]["out"]
    results = replay(baseline_seats, load_live(args.live), args.method)
    results["title"] = args.title
    results["baseline"] = Path(args.baseline).name
    results["live"] = Path(args.live).name
    write_outputs(results, args.out)

    first, last = results["steps"][0], results["steps"][-1]
    print(f"GB declarations used: {last['n']} of {results['gb_seats']}")
    print(f"n={first['n']}  ", _fmt(first["seats"]))
    print(f"n={last['n']}", _fmt(last["seats"]))
    if results["skipped"]:
        print("Skipped:", results["skipped"])
    print(f"Wrote {Path(args.out).with_suffix('.json')} and .html")


def _fmt(seats):
    return "  ".join(f"{p} {n}" for p, n in seats.items() if n)


if __name__ == "__main__":
    main()
