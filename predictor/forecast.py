"""Forecast undeclared Great Britain seats by swing, measured per country.

England, Scotland and Wales each have their own swing. For every declared
seat we compare each party's share of the vote with its share in the same
seat at the previous election; the average of those changes across a
country's declared seats is that country's swing. Each undeclared seat is
predicted by adding its own country's swing to its previous shares and
taking the party with the largest share.

So a Scottish prediction only ever moves when a Scottish seat declares.
Until a country has any declarations, every party there is assumed to be
unchanged (there is no information to say otherwise).

Deliberately simple (to be refined later):
- A party's average change only counts seats where it stood at one or
  both elections.
- The SNP is only predicted in Scotland and Plaid only in Wales.
- Shares pushed below zero are treated as zero.
- Northern Ireland is not used at all.
"""

import math
import statistics

from .parties import GB_PARTIES

COUNTRIES = ("England", "Scotland", "Wales")
ONLY_STANDS_IN = {"SNP": "Scotland", "Plaid": "Wales"}


class Swing:
    """Running average change in vote share across a set of declared seats."""

    def __init__(self):
        self._total = dict.fromkeys(GB_PARTIES, 0.0)
        self._seats = dict.fromkeys(GB_PARTIES, 0)
        self.declared = 0

    def add(self, old_shares, new_shares):
        """Include one newly declared seat."""
        self.declared += 1
        for p in GB_PARTIES:
            if old_shares[p] > 0 or new_shares[p] > 0:
                self._total[p] += new_shares[p] - old_shares[p]
                self._seats[p] += 1

    def change(self, party):
        """Average change in the party's share so far (0 to 1 scale)."""
        seats = self._seats[party]
        return self._total[party] / seats if seats else 0.0

    def changes(self):
        return {p: self.change(p) for p in GB_PARTIES}

    def predict(self, old_shares, country):
        """Predicted winner of an undeclared seat."""
        best, best_share = None, -1.0
        for p in GB_PARTIES:
            if p in ONLY_STANDS_IN and ONLY_STANDS_IN[p] != country:
                continue
            share = max(0.0, old_shares[p] + self.change(p))
            if share > best_share:
                best, best_share = p, share
        return best


class SwingByCountry:
    """A separate Swing for each of England, Scotland and Wales."""

    def __init__(self):
        self.by_country = {c: Swing() for c in COUNTRIES}

    def add(self, country, old_shares, new_shares):
        self.by_country[country].add(old_shares, new_shares)

    def predict(self, old_shares, country):
        return self.by_country[country].predict(old_shares, country)

    def changes(self):
        """{country: {party: change}}, leaving out parties that don't stand there."""
        return {
            c: {p: v for p, v in s.changes().items()
                if p not in ONLY_STANDS_IN or ONLY_STANDS_IN[p] == c}
            for c, s in self.by_country.items()
        }

    def declared(self):
        return {c: s.declared for c, s in self.by_country.items()}


# ---------------------------------------------------------------------------
# Theta method: proportional for losers, proportional on the complement for
# gainers, combined into one number per party.
#
# For a declared seat with previous share x and new share y (0 to 1):
#     theta = ln(y / x)                       if y < x   (losing ground)
#     theta = -ln((1 - y) / (1 - x))          if y >= x  (gaining ground)
# theta is 0 for no change, negative for a loss, positive for a gain.
# A country's theta for a party is the average (mean, or optionally median)
# over its declared seats.
#
# Applied to an undeclared seat with previous share x:
#     theta < 0:  predicted = x * e^theta                (keeps a fixed fraction)
#     theta >= 0: predicted = 1 - (1 - x) * e^(-theta)   (gains a fixed fraction
#                                                         of the vote it lacked)
# Only the order of the predicted shares matters for the winner, so they are
# not rescaled.
# ---------------------------------------------------------------------------


def theta(old, new):
    """Theta for one party in one declared seat, or None if it tells us nothing.

    A party that did not stand this time (new share 0) gives no information,
    nor does a share of exactly 100% (unopposed).
    """
    if new <= 0 or new >= 1 or old >= 1:
        return None
    if new < old:
        return math.log(new / old)
    return -math.log((1 - new) / (1 - old))


def apply_theta(old, th):
    """Predicted share from previous share old and theta th."""
    if th < 0:
        return old * math.exp(th)
    return 1 - (1 - old) * math.exp(-th)


class ThetaSwing:
    """Theta per party across a set of declared seats: the mean (default) or
    the median of the per-seat values."""

    def __init__(self, stat="mean"):
        if stat not in ("mean", "median"):
            raise ValueError(f"unknown statistic {stat!r}")
        self.stat = stat
        self._values = {p: [] for p in GB_PARTIES}
        self.declared = 0

    def add(self, old_shares, new_shares):
        self.declared += 1
        for p in GB_PARTIES:
            th = theta(old_shares[p], new_shares[p])
            if th is not None:
                self._values[p].append(th)

    def change(self, party):
        """Theta so far (0 if the party has no information yet)."""
        v = self._values[party]
        if not v:
            return 0.0
        if self.stat == "mean":
            return sum(v) / len(v)
        return statistics.median(v)

    def changes(self):
        return {p: self.change(p) for p in GB_PARTIES}

    def predict(self, old_shares, country):
        best, best_share = None, -1.0
        for p in GB_PARTIES:
            if p in ONLY_STANDS_IN and ONLY_STANDS_IN[p] != country:
                continue
            share = apply_theta(old_shares[p], self.change(p))
            if share > best_share:
                best, best_share = p, share
        return best


class ThetaByCountry(SwingByCountry):
    """A separate ThetaSwing for each of England, Scotland and Wales."""

    def __init__(self):
        self.by_country = {c: ThetaSwing() for c in COUNTRIES}


# ---------------------------------------------------------------------------
# Theta by seat type: a separate theta for each type of contest, defined by
# the top two parties at the previous election.
# ---------------------------------------------------------------------------

SEAT_TYPES = {
    frozenset(("Con", "Lab")): "Con v Lab",
    frozenset(("Con", "LibDem")): "Con v LibDem",
    frozenset(("Lab", "LibDem")): "Lab v LibDem",
}
MIN_TYPE_SEATS = 5   # declared seats a type needs before it uses its own theta


def seat_type(old_shares):
    """The seat's type from its previous top two parties, or None if not one of SEAT_TYPES."""
    a, b = sorted(old_shares, key=old_shares.get, reverse=True)[:2]
    return SEAT_TYPES.get(frozenset((a, b)))


STRONG_SHARE = 0.60   # previous winner's share for a Con v Lab seat to count as strong
STRENGTH_TYPES = ("Strong Con", "Strong Lab", "Con v Lab", "Con v LibDem", "Lab v LibDem")


def seat_type_with_strength(old_shares):
    """Like seat_type, but Con v Lab seats where the winner had STRONG_SHARE or
    more are split off as "Strong Con" or "Strong Lab"."""
    t = seat_type(old_shares)
    if t == "Con v Lab":
        if old_shares["Con"] >= STRONG_SHARE:
            return "Strong Con"
        if old_shares["Lab"] >= STRONG_SHARE:
            return "Strong Lab"
    return t


class ThetaBySeatType:
    """Theta measured separately for each seat type, within one country.

    A seat of a known type uses that type's theta once MIN_TYPE_SEATS seats of
    the type have declared; until then, and for seats of no listed type, it
    uses the overall theta of all declared seats.
    """

    def __init__(self, stat="mean", classify=seat_type, types=tuple(SEAT_TYPES.values())):
        self.classify = classify
        self.overall = ThetaSwing(stat)
        self.by_type = {t: ThetaSwing(stat) for t in types}

    def add(self, old_shares, new_shares):
        self.overall.add(old_shares, new_shares)
        t = self.classify(old_shares)
        if t is not None:
            self.by_type[t].add(old_shares, new_shares)

    def swing_for(self, old_shares):
        t = self.classify(old_shares)
        if t is not None and self.by_type[t].declared >= MIN_TYPE_SEATS:
            return self.by_type[t]
        return self.overall

    def predict(self, old_shares, country):
        return self.swing_for(old_shares).predict(old_shares, country)
