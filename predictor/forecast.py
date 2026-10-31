"""Forecast undeclared Great Britain seats by simple national swing.

For every declared GB seat we compare each party's share of the vote
with its share in the same seat at the previous election. The average
of those changes is the national swing. Each undeclared seat is then
predicted by adding the swing to its previous shares and taking the
party with the largest share.

Deliberately simple (to be refined later):
- A party's average change only counts seats where it stood at one or
  both elections, so e.g. the SNP's swing is measured in Scotland only.
- The SNP is only predicted in Scotland and Plaid only in Wales.
- Shares pushed below zero are treated as zero.
- Northern Ireland is not used at all.
"""

from .parties import GB_PARTIES

ONLY_STANDS_IN = {"SNP": "Scotland", "Plaid": "Wales"}


class NationalSwing:
    """Running average change in vote share across declared seats."""

    def __init__(self):
        self._total = dict.fromkeys(GB_PARTIES, 0.0)
        self._seats = dict.fromkeys(GB_PARTIES, 0)

    def add(self, old_shares, new_shares):
        """Include one newly declared seat."""
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
