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

To use the theta method instead (written to separate files, so the
uniform-swing graph is kept):

```
python -m predictor.replay --method theta
```

writes `output/replay_2024_theta.json` and `output/replay_2024_theta.html`.

The theta method gives each party one number per country, the average over
that country's declared seats of

- θ = ln(y ÷ x) if the party lost ground (y < x), or
- θ = −ln((1 − y) ÷ (1 − x)) if it gained (y ≥ x),

where x and y are its previous and new shares. An undeclared seat with
previous share x is predicted as x·e^θ if θ < 0 (a loser keeps a fixed
fraction of its vote) or 1 − (1 − x)·e^(−θ) if θ ≥ 0 (a gainer wins a fixed
fraction of the vote it lacked).

## England: forecast seats by method

```
python -m predictor.matrix_replay
```

Writes `output/england_matrix_2024.json` and `.html`: each party's forecast
of England's 543 seats after each English declaration, from n = 30, for
uniform swing, theta, theta by seat type (mean or median) or a vote
transition matrix (chosen with buttons), with
the final result shown as dashed lines. The transition matrix
(T_ab = fraction of party a's 2019 voters now voting for party b) is refitted
from scratch after each declaration by convex least squares (entries ≥ 0,
rows sum to 1), so it depends only on the seats declared so far. Theta by
seat type uses a separate theta for Con v Lab, Con v LibDem and Lab v LibDem
seats (by the 2019 top two parties) once 5 seats of that type have declared;
other seats, and types with fewer than 5 declared, use the overall theta.
The median version uses each party's median per-seat theta instead of the
mean, so a single atypical result barely moves it.

## Scatter of vote share change

```
python -m predictor.scatter
```

Writes `output/scatter_2024.json` and `output/scatter_2024.html`: one dot
per party per GB seat, 2019 share across, change by 2024 up or down.

## Project layout

| Path | What it is |
|---|---|
| `data/UKDecember2019.json` | 2019 notional results on the current boundaries (the baseline) |
| `data/UKJuly2024.json` | 2024 results in declaration order, with five seats' independent votes corrected |
| `data/raw/` | The original files, unchanged |
| `predictor/matching.py` | Matches live constituency names to our seat names |
| `predictor/parties.py` | Translates live party names to our party codes |
| `predictor/forecast.py` | The forecasts: uniform swing and the theta method (each measured separately for England, Scotland and Wales) |
| `predictor/replay.py` | Runs the forecast after every declaration and writes the outputs |
| `predictor/scatter.py` | Builds the vote share change scatter |
| `predictor/matrix.py` | The vote transition matrix fit |
| `predictor/matrix_replay.py` | England-only comparison of the three methods |
| `web/graph_template.html` | The D3 graph page |
| `web/scatter_template.html` | The D3 scatter page |
| `web/england_matrix_template.html` | The D3 England forecast page |
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
