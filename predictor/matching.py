"""Match constituency names from a live feed to our known constituencies.

Live results (e.g. from the BBC on election night) may spell seat names
differently from our data, so names are compared by a normalised key:

1. Clean up characters: repair garbled UTF-8 (e.g. "MÃ´n" -> "Môn"), then
   drop accents (e.g. "Môn" -> "Mon").
2. Lower-case, remove the words "&", "and" and "the", and sort the
   remaining words alphabetically.
   e.g. "Hull North & Cottingham" -> "cottingham hull north"
3. If no known seat has the same key, fall back to a seat whose name
   contains every word of the live name, provided exactly one seat does.
   e.g. "Hull East" -> "Kingston upon Hull East"
"""

import unicodedata

IGNORED_WORDS = {"&", "and", "the"}


def clean_text(name):
    """Repair garbled UTF-8 and remove accents."""
    try:
        name = name.encode("latin-1").decode("utf-8")
    except UnicodeError:
        pass  # not garbled
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def name_words(name):
    """The words of a name that count for matching, in alphabetical order."""
    words = clean_text(name).lower().split()
    return sorted(w for w in words if w not in IGNORED_WORDS)


def name_key(name):
    """Normalised key used to compare two constituency names."""
    return " ".join(name_words(name))


class NoMatchError(LookupError):
    """Raised when a live name matches no known seat, or several."""


class ConstituencyMatcher:
    """Finds the known constituency that a live-feed name refers to."""

    def __init__(self, known_names):
        self.known_names = list(known_names)
        self._by_key = {}
        for name in self.known_names:
            key = name_key(name)
            if key in self._by_key:
                raise ValueError(
                    f"{name!r} and {self._by_key[key]!r} have the same key {key!r}"
                )
            self._by_key[key] = name
        self._word_sets = {name: set(name_words(name)) for name in self.known_names}

    def match(self, live_name):
        """Return the known name for live_name, or raise NoMatchError."""
        exact = self._by_key.get(name_key(live_name))
        if exact is not None:
            return exact

        live_words = set(name_words(live_name))
        candidates = [
            name for name, words in self._word_sets.items() if live_words <= words
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise NoMatchError(f"No constituency matches {live_name!r}")
        raise NoMatchError(
            f"{live_name!r} could be any of: {', '.join(sorted(candidates))}"
        )
