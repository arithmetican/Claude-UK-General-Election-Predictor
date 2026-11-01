"""England-only replay comparing uniform swing, theta, theta by seat type and the
transition matrix.


Usage:
    python -m predictor.matrix_replay

Writes output/england_matrix_2024.json and .html. Only English seats are used,
both for measuring and forecasting. The matrix forecast starts once START
English seats have declared (before that it is not well determined); uniform
swing and theta are shown from the same point for comparison.

After n English declarations each method's total for a party is:
    seats it actually won among the n declared English seats
  + seats it is predicted to win among the 543 - n undeclared English seats.
"""

import json
import logging
from collections import Counter
from pathlib import Path

import numpy as np

from .forecast import STRENGTH_TYPES, Swing, ThetaBySeatType, ThetaSwing, seat_type_with_strength
from .matching import ConstituencyMatcher
from .matrix import ENGLAND_PARTIES, fit_matrix, predict_shares
from .parties import INDEPENDENT, read_votes, vote_shares
from .replay import ROOT, load_baseline, load_live

START = 30
TEMPLATE = ROOT / "web" / "england_matrix_template.html"
OUT = ROOT / "output" / "england_matrix_2024"
PARTIES = list(ENGLAND_PARTIES[:-1]) + [INDEPENDENT, "Others"]


def english_results(baseline_seats, live_results):
    """English declarations in order: (seat, previous shares, new shares, winner)."""
    matcher = ConstituencyMatcher(baseline_seats)
    out, seen = [], set()
    for live_name, live_votes in live_results:
        seat = matcher.match(live_name)
        if seat is None or seat in seen or baseline_seats[seat]["country"] != "England":
            continue
        votes, winner = read_votes(live_votes)
        new = vote_shares(votes)
        if new is None:
            continue
        seen.add(seat)
        out.append((seat, baseline_seats[seat]["shares"], new, winner))
    return out


def run(baseline_seats, live_results, start=START):
    rows = english_results(baseline_seats, live_results)
    seats = [r[0] for r in rows]
    X = np.array([[r[1][p] for p in ENGLAND_PARTIES] for r in rows])
    Y = np.array([[r[2][p] for p in ENGLAND_PARTIES] for r in rows])
    M = (Y > 0).astype(float)          # who stood (known in advance from nominations)
    actual = [r[3] for r in rows]
    final = Counter(actual)

    uniform, theta, theta_type = Swing(), ThetaSwing(), ThetaBySeatType()
    theta_type_median = ThetaBySeatType("median")
    theta_strong = ThetaBySeatType("median", seat_type_with_strength, STRENGTH_TYPES)
    steps = []
    for n, (seat, old, new, winner) in enumerate(rows, start=1):
        uniform.add(old, new)
        theta.add(old, new)
        theta_type.add(old, new)
        theta_type_median.add(old, new)
        theta_strong.add(old, new)
        if n < start:
            continue
        T = fit_matrix(X[:n], Y[:n], M[:n])   # from scratch: depends only on these n seats
        declared = Counter(actual[:n])
        rest = range(n, len(rows))
        pred = {
            "uniform": Counter(uniform.predict(rows[i][1], "England") for i in rest),
            "theta": Counter(theta.predict(rows[i][1], "England") for i in rest),
            "theta_type": Counter(theta_type.predict(rows[i][1], "England") for i in rest),
            "theta_type_median": Counter(theta_type_median.predict(rows[i][1], "England") for i in rest),
            "theta_strong": Counter(theta_strong.predict(rows[i][1], "England") for i in rest),
            "matrix": Counter(ENGLAND_PARTIES[k] for k in
                              predict_shares(X[n:], T, M[n:]).argmax(axis=1)) if n < len(rows) else Counter(),
        }
        steps.append({
            "n": n, "seat": seat, "winner": winner,
            "seats": {m: {p: declared[p] + c[p] for p in PARTIES} for m, c in pred.items()},
            "matrix": [[round(float(v), 4) for v in row] for row in T],
        })
    return {
        "title": "England only: does a transition matrix remove the bias?",
        "england_seats": len(rows),
        "start": start,
        "parties": PARTIES,
        "matrix_parties": list(ENGLAND_PARTIES),
        "final": {p: final[p] for p in PARTIES},
        "steps": steps,
    }


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    _, baseline_seats = load_baseline(ROOT / "data" / "UKDecember2019.json")
    results = run(baseline_seats, load_live(ROOT / "data" / "UKJuly2024.json"))
    results["baseline"], results["live"] = "UKDecember2019.json", "UKJuly2024.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT.with_suffix(".json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
        f.write("\n")
    data = json.dumps(results, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*RESULTS*/null", data)
    OUT.with_suffix(".html").write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.with_suffix('.json')} and .html ({len(results['steps'])} steps)")


if __name__ == "__main__":
    main()
