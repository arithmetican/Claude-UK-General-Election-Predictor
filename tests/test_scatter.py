"""Tests for the scatter data."""

import unittest
from pathlib import Path

from predictor.replay import load_baseline, load_live
from predictor.scatter import scatter_points

DATA = Path(__file__).resolve().parent.parent / "data"


class ScatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, seats = load_baseline(DATA / "UKDecember2019.json")
        cls.points = scatter_points(seats, load_live(DATA / "UKJuly2024.json"))

    def test_every_gb_seat_and_no_ni(self):
        self.assertEqual(len({p["seat"] for p in self.points}), 632)
        self.assertNotIn("Northern Ireland", {p["country"] for p in self.points})

    def test_known_point(self):
        p = next(p for p in self.points if p["seat"] == "Sunderland Central" and p["party"] == "Lab")
        self.assertEqual((p["order"], p["country"]), (1, "England"))

    def test_party_only_where_it_stood(self):
        self.assertTrue(all(p["old"] > 0 or p["new"] > 0 for p in self.points))
        self.assertTrue(all(p["country"] == "Scotland" for p in self.points if p["party"] == "SNP"))


if __name__ == "__main__":
    unittest.main()
