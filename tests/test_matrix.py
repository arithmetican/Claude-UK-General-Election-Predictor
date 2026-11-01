"""Tests for the transition matrix fit."""

import unittest
from pathlib import Path

import numpy as np

from predictor.matrix import ENGLAND_PARTIES as P, fit_matrix, predict_shares
from predictor.matrix_replay import english_results, run
from predictor.replay import load_baseline, load_live

DATA = Path(__file__).resolve().parent.parent / "data"


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.seats = load_baseline(DATA / "UKDecember2019.json")
        cls.live = load_live(DATA / "UKJuly2024.json")
        rows = english_results(cls.seats, cls.live)
        cls.X = np.array([[r[1][p] for p in P] for r in rows])
        cls.Y = np.array([[r[2][p] for p in P] for r in rows])
        cls.M = (cls.Y > 0).astype(float)

    def test_valid_matrix(self):
        T = fit_matrix(self.X[:50], self.Y[:50], self.M[:50])
        self.assertTrue((T >= 0).all())
        np.testing.assert_allclose(T.sum(axis=1), 1, atol=1e-9)

    def test_depends_only_on_the_declared_seats_not_their_order(self):
        perm = np.random.default_rng(0).permutation(80)
        T1 = fit_matrix(self.X[:80], self.Y[:80], self.M[:80])
        T2 = fit_matrix(self.X[:80][perm], self.Y[:80][perm], self.M[:80][perm])
        np.testing.assert_allclose(T1, T2, atol=1e-9)

    def test_recovers_a_known_matrix(self):
        rng = np.random.default_rng(1)
        X = rng.dirichlet(np.ones(6), size=60)
        T_true = rng.dirichlet(np.ones(6) * 0.5, size=6) * 0.4 + np.eye(6) * 0.6
        Y = X @ T_true
        np.testing.assert_allclose(fit_matrix(X, Y, np.ones_like(Y)), T_true, atol=1e-3)

    def test_non_standing_party_gets_nothing(self):
        T = fit_matrix(self.X[:50], self.Y[:50], self.M[:50])
        mask = np.ones((1, 6)); mask[0, 3] = 0
        self.assertEqual(predict_shares(self.X[:1], T, mask)[0, 3], 0)

    def test_replay_converges_to_final(self):
        r = run(self.seats, self.live)
        last = r["steps"][-1]["seats"]
        for method in ("uniform", "theta", "theta_type", "matrix"):
            self.assertEqual(last[method], r["final"])


if __name__ == "__main__":
    unittest.main()
