"""Tests for the theta method."""

import math
import unittest
from pathlib import Path

from predictor.forecast import MIN_TYPE_SEATS, ThetaBySeatType, ThetaSwing, apply_theta, seat_type, theta
from predictor.parties import vote_shares
from predictor.replay import load_baseline, load_live, replay

DATA = Path(__file__).resolve().parent.parent / "data"


class ThetaFormulaTests(unittest.TestCase):
    def test_round_trip(self):
        for old, new in ((0.6061, 0.2848), (0.3152, 0.3692), (0.0, 0.2198), (0.4, 0.4)):
            self.assertAlmostEqual(apply_theta(old, theta(old, new)), new)

    def test_sign_and_known_values(self):
        self.assertAlmostEqual(theta(0.5, 0.25), math.log(0.5))     # loser keeps half
        self.assertAlmostEqual(theta(0.5, 0.75), -math.log(0.5))    # gainer wins half its non-vote
        self.assertEqual(theta(0.3, 0.3), 0.0)

    def test_no_information(self):
        self.assertIsNone(theta(0.2, 0.0))   # did not stand this time
        self.assertIsNone(theta(0.0, 1.0))   # unopposed

    def test_shares_stay_between_0_and_1(self):
        for old in (0.0, 0.01, 0.5, 0.99):
            for th in (-5, -0.5, 0, 0.5, 5):
                self.assertTrue(0 <= apply_theta(old, th) <= 1)

    def test_one_seat_reproduces_it_exactly(self):
        swing = ThetaSwing()
        old = vote_shares({"Lab": 40, "Con": 50, "Reform": 0, "Others": 10})
        new = vote_shares({"Lab": 45, "Con": 25, "Reform": 20, "Others": 10})
        swing.add(old, new)
        for p in ("Lab", "Con", "Reform"):
            self.assertAlmostEqual(apply_theta(old[p], swing.change(p)), new[p])


class SeatTypeTests(unittest.TestCase):
    def test_types_from_top_two(self):
        self.assertEqual(seat_type({"Con": .5, "Lab": .3, "LibDem": .1}), "Con v Lab")
        self.assertEqual(seat_type({"Lab": .5, "Con": .3, "LibDem": .1}), "Con v Lab")
        self.assertEqual(seat_type({"Con": .5, "LibDem": .4, "Lab": .1}), "Con v LibDem")
        self.assertEqual(seat_type({"LibDem": .5, "Lab": .4, "Con": .1}), "Lab v LibDem")
        self.assertIsNone(seat_type({"Lab": .5, "Reform": .3, "Con": .1}))

    def test_type_theta_used_only_after_enough_seats(self):
        swing = ThetaBySeatType()
        old = vote_shares({"Con": 50, "LibDem": 40, "Lab": 10})
        new = vote_shares({"Con": 30, "LibDem": 60, "Lab": 10})
        for i in range(MIN_TYPE_SEATS):
            self.assertIs(swing.swing_for(old), swing.overall)
            swing.add(old, new)
        self.assertIs(swing.swing_for(old), swing.by_type["Con v LibDem"])
        self.assertIs(swing.swing_for(vote_shares({"Lab": 50, "Reform": 30})), swing.overall)


class ThetaReplayTests(unittest.TestCase):
    def test_replay_ends_at_actual_result(self):
        _, seats = load_baseline(DATA / "UKDecember2019.json")
        steps = replay(seats, load_live(DATA / "UKJuly2024.json"), "theta")["steps"]
        last = {p: n for p, n in steps[-1]["seats"].items() if n}
        self.assertEqual(last, {"Lab": 411, "Con": 121, "LibDem": 72, "SNP": 9,
                                "Reform": 5, "Independent": 5, "Green": 4,
                                "Plaid": 4, "Others": 1})
        self.assertTrue(all(sum(s["seats"].values()) == 632 for s in steps))


if __name__ == "__main__":
    unittest.main()
