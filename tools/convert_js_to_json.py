"""Convert a JavaScript election-results file into tidy JSON.

Usage:
    python tools/convert_js_to_json.py data/raw/UKDecember2019.js data/UKDecember2019.json

The input is a JavaScript array assignment like:

    const UKDecember2019 = [
      ["Prefix", "UKGeneralElection"],
      ["Month", "December"],
      ["Year", "2019"],
      ["Constituency Results", [
        [["Constituency", "Aberafan Maesteg"], ["Region", "Wales"], ...],
        ...
      ]]
    ]

The output is a JSON object with the election details and one record
per constituency, with vote counts as numbers and blank entries removed.
"""

import json
import re
import sys

INFO_FIELDS = {"Constituency", "Region", "Country"}


def parse_js_array(text):
    """Turn the JavaScript array literal into Python lists."""
    # Keep only the array: from the first "[" to the last "]".
    start, end = text.index("["), text.rindex("]")
    body = text[start:end + 1]
    # JavaScript allows trailing commas ("..., ]"); JSON does not.
    body = re.sub(r",\s*\]", "]", body)
    return json.loads(body)


def convert_seat(pairs):
    """Turn one constituency's [key, value] pairs into a tidy record."""
    seat = {"votes": {}}
    for key, value in pairs:
        if key in INFO_FIELDS:
            seat[key.lower()] = value
            continue
        if value == "":
            continue  # party did not stand here
        party = "Others" if key.lower() == "others" else key
        seat["votes"][party] = seat["votes"].get(party, 0) + int(value)
    # Put the descriptive fields first for readability.
    return {
        "constituency": seat["constituency"],
        "region": seat["region"],
        "country": seat["country"],
        "votes": seat["votes"],
    }


def convert(data):
    header = {}
    seats = []
    for key, value in data:
        if key == "Constituency Results":
            seats = [convert_seat(pairs) for pairs in value]
        else:
            header[key.lower()] = value
    return {
        "election": header.get("prefix"),
        "month": header.get("month"),
        "year": int(header["year"]) if "year" in header else None,
        "constituencies": seats,
    }


def main(src, dest):
    with open(src, encoding="utf-8") as f:
        data = parse_js_array(f.read())
    result = convert(data)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(result['constituencies'])} constituencies to {dest}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
