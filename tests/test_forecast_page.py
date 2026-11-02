"""Tests for the switchable GB forecast page and its models."""

import unittest
from pathlib import Path

from predictor.forecast import (CountryModel, MIN_TYPE_SEATS, Swing, ThetaBySeatType, ThetaSwing,
                                type_classifier)
from predictor.forecast_page import OPTIONS, expand, make_model
from predictor.parties import vote_shares
from predictor.replay import load_baseline, load_live, replay

DATA = Path(__file__).resolve().parent.parent / "data"


def choice(**kw):
    c = {o["name"]: o["values"][0]["value"] for o in OPTIONS}
    c.update(kw)
    return c


class MedianSwingTests(unittest.TestCase):
    def test_median_of_per_seat_changes(self):
        swing = Swing("median")
        old = vote_shares({"Lab": 40, "Con": 60})
        for lab in (42, 44, 46, 80):            # changes +2, +4, +6, +40 points
            swing.add(old, vote_shares({"Lab": lab, "Con": 100 - lab}))
        self.assertAlmostEqual(swing.change("Lab"), 0.05)     # median of 2, 4, 6, 40
        self.assertAlmostEqual(Swing().change("Lab"), 0.0)

    def test_unknown_statistic_rejected(self):
        with self.assertRaises(ValueError):
            Swing("mode")


class TypeSwitchTests(unittest.TestCase):
    def test_only_enabled_types_are_used(self):
        classify = type_classifier(["Con v LibDem"])
        self.assertEqual(classify(vote_shares({"Con": 50, "LibDem": 40, "Lab": 10})), "Con v LibDem")
        self.assertIsNone(classify(vote_shares({"Con": 50, "Lab": 40, "LibDem": 10})))

    def test_types_apply_in_england_only(self):
        m = CountryModel(lambda: ThetaSwing("median"), ["Con v Lab"])
        old = vote_shares({"Con": 50, "Lab": 40, "LibDem": 10})
        new = vote_shares({"Con": 30, "Lab": 60, "LibDem": 10})
        for _ in range(MIN_TYPE_SEATS):
            m.add("Scotland", old, new)
            m.add("England", old, new)
        self.assertIsInstance(m.by_country["Scotland"], ThetaSwing)          # no types in Scotland
        self.assertIs(m.by_country["England"].swing_for(old),
                      m.by_country["England"].by_type["Con v Lab"])          # own figure after 5 seats


class ForecastPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.seats = load_baseline(DATA / "UKDecember2019.json")
        cls.live = load_live(DATA / "UKJuly2024.json")

    def run_choice(self, **kw):
        c = choice(**kw)
        method = "theta" if c["transfer"] == "proportional" else "uniform"
        return replay(self.seats, self.live, method, make=make_model(c))["steps"]

    def test_base_model_matches_original_uniform_replay(self):
        base = self.run_choice()
        original = replay(self.seats, self.live)["steps"]
        self.assertEqual([s["seats"] for s in base], [s["seats"] for s in original])

    def test_proportional_mean_matches_theta_replay(self):
        prop = self.run_choice(transfer="proportional")
        theta = replay(self.seats, self.live, "theta")["steps"]
        self.assertEqual([s["seats"] for s in prop], [s["seats"] for s in theta])

    def test_all_three_types_match_england_seat_type_model_in_england(self):
        # With every type switched on, England uses the same grouping as the
        # England-only seat-type model; the totals must still end at the result.
        steps = self.run_choice(transfer="proportional", average="median",
                                conlab="on", conlib="on", lablib="on")
        last = {p: n for p, n in steps[-1]["seats"].items() if n}
        self.assertEqual(last, {"Lab": 411, "Con": 121, "LibDem": 72, "SNP": 9, "Reform": 5,
                                "Independent": 5, "Green": 4, "Plaid": 4, "Others": 1})
        self.assertTrue(all(sum(s["seats"].values()) == 632 for s in steps))

    def test_compact_storage_round_trips(self):
        from predictor.forecast_page import build
        import predictor.forecast_page as fp
        saved = fp.OPTIONS
        try:
            fp.OPTIONS = [o for o in saved if o["name"] in ("transfer", "average")]
            data = build(self.seats, self.live)
            for key in data["variants"]:
                full = expand(data, key)
                names = [o["name"] for o in fp.OPTIONS]
                c = dict(kv.split("=") for kv in key.split("&"))
                c.update({n: "off" for n in ("conlab", "conlib", "lablib")})
                method = "theta" if c["transfer"] == "proportional" else "uniform"
                direct = replay(self.seats, self.live, method, make=make_model(c))["steps"]
                self.assertEqual([s["seats"] for s in full["steps"]], [s["seats"] for s in direct])
                self.assertEqual([s["swing"] for s in full["steps"]], [s["swing"] for s in direct])
        finally:
            fp.OPTIONS = saved


if __name__ == "__main__":
    unittest.main()
