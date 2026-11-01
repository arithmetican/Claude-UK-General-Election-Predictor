"""Vote transition matrix forecast (England only, for now).

T[a, b] is the fraction of party a's previous voters who now vote for party b.
Every entry is 0 or more and each row sums to 1. For a seat with previous
shares x (a row vector), the predicted shares are x T; parties not standing
in the seat are then ignored.

Fitting (convex, solved from scratch every time):
    minimise   sum over declared seats j, parties b standing in j,
                   (sum_a x_aj T_ab - y_bj)^2
             + EPS * sum_ab (T_ab - I_ab)^2
    subject to T_ab >= 0 and sum_b T_ab = 1 for every a.

The objective is quadratic in T and the constraints are linear, so it is a
convex problem with a single best answer. The tiny EPS term (a pull towards
"everyone stays loyal", the identity matrix I) makes that answer unique even
when the declared seats cannot tell some flows apart. There is no starting
point: the matrix after n declarations depends only on those n seats.

It is solved as a non-negative least-squares problem, with the row-sum
constraints added as heavily weighted equations.

Which parties stand in each seat is taken as known in advance (on the night,
from the published nominations; in the replay, from the results).
"""

import numpy as np
from scipy.optimize import nnls

ENGLAND_PARTIES = ("Lab", "Con", "LibDem", "Reform", "Green", "Others")
EPS = 1e-4            # weight of the pull towards the identity matrix
ROW_SUM_WEIGHT = 1e3  # weight of the "each row sums to 1" equations


def fit_matrix(X, Y, M):
    """Best transition matrix for previous shares X, new shares Y, standing mask M.

    X, Y, M: arrays of shape (seats, parties). Returns T of shape (parties, parties).
    """
    n, k = X.shape
    rows, rhs = [], []
    # Data equations: for each seat j and standing party b,
    #   sum_a X[j, a] * T[a, b] = Y[j, b]
    # with the unknowns ordered as t[a * k + b] = T[a, b].
    for j in range(n):
        for b in range(k):
            if not M[j, b]:
                continue
            r = np.zeros(k * k)
            r[np.arange(k) * k + b] = X[j]
            rows.append(r)
            rhs.append(Y[j, b])
    # Pull towards the identity: sqrt(EPS) * (T[a, b] - I[a, b]) = 0
    s = np.sqrt(EPS)
    for a in range(k):
        for b in range(k):
            r = np.zeros(k * k)
            r[a * k + b] = s
            rows.append(r)
            rhs.append(s * (1.0 if a == b else 0.0))
    # Each row sums to 1
    for a in range(k):
        r = np.zeros(k * k)
        r[a * k:(a + 1) * k] = ROW_SUM_WEIGHT
        rows.append(r)
        rhs.append(ROW_SUM_WEIGHT)
    t, _ = nnls(np.array(rows), np.array(rhs), maxiter=50 * k * k)
    T = t.reshape(k, k)
    return T / T.sum(axis=1, keepdims=True)   # remove any tiny row-sum residue


def predict_shares(X, T, M):
    """Predicted shares x T, with parties not standing set to 0."""
    return (X @ T) * M
