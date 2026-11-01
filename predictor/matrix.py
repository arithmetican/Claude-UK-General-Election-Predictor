"""Vote transition matrix forecast (England only, for now).

WORK IN PROGRESS: the softmax parametrisation plus rescaling makes the fit
non-convex, so the fitted matrix depends on the optimiser's starting point.
To be replaced by a convex constrained least-squares fit.

T[a, b] is the fraction of party a's previous voters who now vote for party b.
Each row is non-negative and sums to 1. For a seat with previous shares x
(a row vector), the predicted shares are x T, restricted to the parties
standing in that seat and rescaled to sum to 1.

Fitting: T is chosen to minimise, over the declared seats,
    sum over seats j, parties b of (y_bj - predicted_bj)^2
with every seat counting equally. Each row of T is written as a softmax of
unconstrained numbers W[a, :], so any W gives a valid matrix and the
optimiser can search freely.

Which parties stand in each seat is taken as known in advance (on the night,
from the published nominations; in the replay, from the results).
"""

import numpy as np
from scipy.optimize import minimize

ENGLAND_PARTIES = ("Lab", "Con", "LibDem", "Reform", "Green", "Others")


def softmax_rows(W):
    E = np.exp(W - W.max(axis=1, keepdims=True))
    return E / E.sum(axis=1, keepdims=True)


def predict_shares(X, T, M):
    """X: seats x parties previous shares; M: 1 where the party stands now."""
    raw = (X @ T) * M
    total = raw.sum(axis=1, keepdims=True)
    return np.divide(raw, total, out=np.zeros_like(raw), where=total > 0)


class TransitionMatrix:
    def __init__(self, parties=ENGLAND_PARTIES):
        self.parties = list(parties)
        k = len(self.parties)
        # Start from "everyone stays loyal": a strong diagonal.
        self.W = np.eye(k) * 4.0
        self.T = softmax_rows(self.W)

    def fit(self, X, Y, M):
        """X, Y: previous and new shares of the declared seats; M: who stood."""
        k = len(self.parties)

        def loss_and_grad(w):
            W = w.reshape(k, k)
            T = softmax_rows(W)
            raw = (X @ T) * M
            s = raw.sum(axis=1, keepdims=True)
            P = raw / s
            R = P - Y                                  # residuals
            # d loss / d raw, through the rescaling P = raw / s
            dP = 2 * R
            draw = (dP - (dP * P).sum(axis=1, keepdims=True)) / s
            dT = X.T @ (draw * M)
            # through the softmax of each row
            dW = T * (dT - (dT * T).sum(axis=1, keepdims=True))
            return (R ** 2).sum(), dW.ravel()

        res = minimize(loss_and_grad, self.W.ravel(), jac=True, method="L-BFGS-B")
        self.W = res.x.reshape(k, k)
        self.T = softmax_rows(self.W)
        return res.fun

    def predict(self, X, M):
        return predict_shares(X, self.T, M)
