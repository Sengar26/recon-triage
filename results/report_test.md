# Evaluation report: test set

Scored on the test set, 350 held-out exceptions · seed 42 · model gpt-4.1-mini · 2026-09-25

| Break type | n | Rules baseline | Agent |
|---|---|---|---|
| timing | 61 | 68.9% | 100.0% |
| fx_difference | 57 | 75.4% | 96.5% |
| partial_payment | 54 | 92.6% | 100.0% |
| duplicate | 57 | 64.9% | 70.2% |
| transposition | 61 | 100.0% | 98.4% |
| missing_entry | 60 | 58.3% | 100.0% |
| **Overall** | **350** | **76.6%** | **94.3%** |
| Hard cases only | 105 | 21.9% | 84.8% |
| Labelled unclear | | 22.0% | 0.0% |

- **Lift:** +17.7 percentage points (agent minus rules)
- **Ungrounded notes:** 0 of 350 (a note citing a number no tool returned)
- **Cost:** $0.78 estimated, $0.0022 per exception, 3.3 tool calls on average
- **Auto-match rate:** 94.04% of all ledger rows cleared by SQL before any exception reached the agent (5,000 synthetic transactions)

## Agent accuracy by stated confidence

| Confidence | n | Accuracy |
|---|---|---|
| high | 348 | 94.5% |
| medium | 2 | 50.0% |
| low | 0 | n/a |

## Confusion matrix: agent (rows = true type)

| true \ predicted | timing | fx | partial | dup | transp | missing | unclear |
|---|---|---|---|---|---|---|---|
| timing | 61 | 0 | 0 | 0 | 0 | 0 | 0 |
| fx_difference | 0 | 55 | 2 | 0 | 0 | 0 | 0 |
| partial_payment | 0 | 0 | 54 | 0 | 0 | 0 | 0 |
| duplicate | 13 | 0 | 0 | 40 | 0 | 4 | 0 |
| transposition | 0 | 0 | 1 | 0 | 60 | 0 | 0 |
| missing_entry | 0 | 0 | 0 | 0 | 0 | 60 | 0 |

## Confusion matrix: rules baseline (rows = true type)

| true \ predicted | timing | fx | partial | dup | transp | missing | unclear |
|---|---|---|---|---|---|---|---|
| timing | 42 | 0 | 0 | 0 | 0 | 0 | 19 |
| fx_difference | 0 | 43 | 0 | 0 | 0 | 0 | 14 |
| partial_payment | 0 | 4 | 50 | 0 | 0 | 0 | 0 |
| duplicate | 1 | 0 | 0 | 37 | 0 | 0 | 19 |
| transposition | 0 | 0 | 0 | 0 | 61 | 0 | 0 |
| missing_entry | 0 | 0 | 0 | 0 | 0 | 35 | 25 |

## Coverage

- Exceptions scored: 350
- Exceptions with no planted break behind them (excluded): 0
- Planted breaks that never surfaced as an exception: 0
