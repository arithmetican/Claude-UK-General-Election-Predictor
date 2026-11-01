"""Tests for the switchable GB forecast page."""

import json
import unittest
from pathlib import Path

from predictor.forecast import Swing
from predictor.forecast_page import OPTIONS, build
from predictor.parties import vote_shares
from predictor.replay import load_baseline, load_live, replay

DATA = Path(__file__).resolve().parent.parent / "data"


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


class ForecastPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.seats = load_baseline(DATA / "UKDecember2019.json")
        cls.live = load_live(DATA / "UKJuly2024.json")
        cls.data = build(cls.seats, cls.live)

    def test_one_variant_per_combination(self):
        expected = 1
        for o in OPTIONS:
            expected *= len(o["values"])
        self.assertEqual(len(self.data["variants"]), expected)

    def test_base_model_matches_original_uniform_replay(self):
        base = self.data["variants"]["transfer=uniform&average=mean"]["steps"]
        original = replay(self.seats, self.live)["steps"]
        self.assertEqual([s["seats"] for s in base], [s["seats"] for s in original])

    def test_proportional_mean_matches_theta_replay(self):
        prop = self.data["variants"]["transfer=proportional&average=mean"]["steps"]
        theta = replay(self.seats, self.live, "theta")["steps"]
        self.assertEqual([s["seats"] for s in prop], [s["seats"] for s in theta])

    def test_every_variant_ends_at_actual_result(self):
        finals = {json.dumps(v["steps"][-1]["seats"], sort_keys=True) for v in self.data["variants"].values()}
        self.assertEqual(len(finals), 1)


if __name__ == "__main__":
    unittest.main()
