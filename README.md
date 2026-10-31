# UK General Election Predictor

Predicts the final House of Commons as constituency results come in on
election night.

After **n** Great Britain seats have declared, each party's total is the
seats it has actually won plus the seats it is predicted to win among the
632 − n GB seats still to declare. The prediction uses simple swing,
measured separately for England, Scotland and Wales: the average change in
each party's vote share across that country's declared seats, compared with
the same seats at the previous election, applied to that country's
undeclared seats. A country with no declarations yet is assumed unchanged.

Northern Ireland's 18 seats are not used in the prediction or drawn on
the graph, but they still count towards the 650 seats in the House, so a
majority is 326.

## Run the 2024 replay

```
python -m predictor.replay
```

This replays the July 2024 results in declaration order against the
December 2019 notional results and writes:

- `output/replay_2024.json`: seat totals and swing after every declaration
- `output/replay_2024.html`: the graph (open it in a browser)

## Project layout

| Path | What it is |
|---|---|
| `data/UKDecember2019.json` | 2019 notional results on the current boundaries (the baseline) |
| `data/UKJuly2024.json` | 2024 results in declaration order, with five seats' independent votes corrected |
| `data/raw/` | The original files, unchanged |
| `predictor/matching.py` | Matches live constituency names to our seat names |
| `predictor/parties.py` | Translates live party names to our party codes |
| `predictor/forecast.py` | The swing forecast (one swing each for England, Scotland and Wales) |
| `predictor/replay.py` | Runs the forecast after every declaration and writes the outputs |
| `web/graph_template.html` | The D3 graph page |
| `tools/convert_js_to_json.py` | Converts the JavaScript results format to JSON |
| `tests/` | Checks; run with `python -m unittest` |

## Current rules (to be revisited)

- Parties drawn: Labour, Conservative, Lib Dem, Reform, Green, SNP,
  Plaid Cymru, Independent and Others.
- Minor parties, losing independents and the Speaker count as Others.
  An independent who wins a seat counts as Independent.
- Live data is never changed; names are translated as it is read.
- A bad or unmatched live result is logged and skipped, never stopping
  the program. A fault in our own baseline data does stop it.
