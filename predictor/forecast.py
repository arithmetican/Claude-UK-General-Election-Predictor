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
