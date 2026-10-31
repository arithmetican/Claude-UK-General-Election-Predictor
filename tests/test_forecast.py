"""Tests for party translation, the swing forecast and the 2024 replay."""

import unittest
from pathlib import Path

from predictor.forecast import NationalSwing
from predictor.parties import party_code, read_votes, vote_shares
from predictor.replay import load_baseline, load_live, replay

DATA = Path(__file__).resolve().parent.parent / "data"


class PartyTests(unittest.TestCase):
    def test_live_names(self):
        self.assertEqual(party_code("Scottish National Party"), "SNP")
        self.assertEqual(party_code("Liberal Democrat"), "LibDem")
        self.assertEqual(party_code("Workers Party of Britain"), "Others")
        self.assertEqual(party_code("Traditional Unionist Voice"), "Others")
        self.assertEqual(party_code(None), "Others")

    def test_winning_independent_kept_losing_one_in_others(self):
        votes, winner = read_votes({"Independent": "24120", "Labour": "16873"})
        self.assertEqual(winner, "Independent")
        self.assertEqual(votes["Others"], 24120)
        votes, winner = read_votes({"Labour": "200", "Independent": "50"})
        self.assertEqual(winner, "Lab")

    def test_small_parties_added_together_cannot_win(self):
        _, winner = read_votes({"Labour": "40", "A": "30", "B": "30", "C": "30"})
        self.assertEqual(winner, "Lab")

    def test_bad_vote_counts_never_raise(self):
        votes, winner = read_votes({"Labour": "1,234", "Green": "n/a", "Con": None})
        self.assertEqual((votes["Lab"], winner), (1234, "Lab"))
        self.assertEqual(read_votes("rubbish")[1], None)


class SwingTests(unittest.TestCase):
    def test_average_change_applied(self):
        swing = NationalSwing()
        old = vote_shares({"Lab": 40, "Con": 50, "Others": 10})
        new = vote_shares({"Lab": 50, "Con": 40, "Others": 10})
        swing.add(old, new)
        self.assertAlmostEqual(swing.change("Lab"), 0.10)
        self.assertEqual(swing.predict(old, "England"), "Lab")

    def test_snp_only_predicted_in_scotland(self):
        swing = NationalSwing()
        shares = vote_shares({"SNP": 60, "Lab": 40})
        self.assertEqual(swing.predict(shares, "Scotland"), "SNP")
        self.assertEqual(swing.predict(shares, "England"), "Lab")


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, seats = load_baseline(DATA / "UKDecember2019.json")
        cls.results = replay(seats, load_live(DATA / "UKJuly2024.json"))

    def test_uses_every_gb_seat_and_no_ni_seat(self):
        self.assertEqual(self.results["steps"][-1]["n"], 632)
        self.assertEqual(len(self.results["ni_declared"]), 18)
        self.assertEqual(self.results["skipped"], [])

    def test_starts_at_first_declaration_and_ends_at_actual_2024(self):
        steps = self.results["steps"]
        self.assertEqual([s["n"] for s in steps], list(range(1, 633)))
        self.assertEqual(steps[0]["seat"], "Sunderland Central")
        last = {p: n for p, n in steps[-1]["seats"].items() if n}
        self.assertEqual(last, {"Lab": 411, "Con": 121, "LibDem": 72, "SNP": 9,
                                "Reform": 5, "Independent": 5, "Green": 4,
                                "Plaid": 4, "Others": 1})

    def test_every_step_adds_up_to_632(self):
        for step in self.results["steps"]:
            self.assertEqual(sum(step["seats"].values()), 632)


if __name__ == "__main__":
    unittest.main()
