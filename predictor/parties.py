"""Translate live-feed party names into the party codes used by our data.

The live feed (e.g. the BBC) uses full names such as "Labour" or
"Scottish National Party"; our 2019 data uses short codes such as "Lab"
and "SNP". The live data itself is never changed; names are translated
as it is read.

Current rules (to be revisited):
- The seven main Great Britain parties keep their own codes.
- An independent who WINS a seat counts as "Independent".
- Everything else (minor parties, losing independents, the Speaker)
  counts as "Others".

Reading live data never raises an error: unreadable vote counts are
logged and skipped.
"""

import logging

log = logging.getLogger(__name__)

# Parties drawn on the graph, in the order they are listed.
GB_PARTIES = ("Lab", "Con", "LibDem", "Reform", "Green", "SNP", "Plaid", "Others")
INDEPENDENT = "Independent"
OTHERS = "Others"

# Live name (lower case, trimmed) -> our code. Codes map to themselves too.
LIVE_NAMES = {
    "labour": "Lab",
    "labour party": "Lab",
    "conservative": "Con",
    "conservatives": "Con",
    "conservative and unionist party": "Con",
    "liberal democrat": "LibDem",
    "liberal democrats": "LibDem",
    "reform": "Reform",
    "reform uk": "Reform",
    "green": "Green",
    "green party": "Green",
    "scottish national party": "SNP",
    "plaid cymru": "Plaid",
    "independent": INDEPENDENT,
}
LIVE_NAMES.update({code.lower(): code for code in GB_PARTIES})


def party_code(live_name):
    """Our code for a live party name: a main party, Independent or Others."""
    if not isinstance(live_name, str):
        return OTHERS
    return LIVE_NAMES.get(live_name.strip().lower(), OTHERS)


def read_votes(live_votes):
    """Turn one seat's live results into (votes, winner).

    live_votes: {party name: votes} as given by the feed; votes may be text.
    votes:      {code: total} over GB_PARTIES, with independents in Others.
    winner:     code of the party whose candidate came top, or None.
                A winning independent is "Independent"; a winning minor
                party is "Others".
    """
    votes = dict.fromkeys(GB_PARTIES, 0)
    winner, winner_votes = None, -1
    if not isinstance(live_votes, dict):
        log.warning("Seat results are not a list of parties: %r", live_votes)
        return votes, None

    for name, value in live_votes.items():
        try:
            count = int(str(value).replace(",", "").strip())
        except ValueError:
            log.warning("Unreadable vote count %r for %r", value, name)
            continue
        code = party_code(name)
        votes[OTHERS if code == INDEPENDENT else code] += count
        # The winner is decided candidate by candidate, not by party group,
        # so many small parties added together can never "win" a seat.
        if count > winner_votes:
            winner, winner_votes = code, count

    return votes, winner


def vote_shares(votes):
    """Each party's share of the vote (0 to 1), or None if no votes."""
    total = sum(votes.get(p, 0) for p in GB_PARTIES)
    if total <= 0:
        return None
    return {p: votes.get(p, 0) / total for p in GB_PARTIES}
