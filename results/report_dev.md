# Evaluation report: dev set

Scored on the dev set, 50 exceptions · seed 42 · model gpt-4.1-mini · 2026-09-25

| Break type | n | Rules baseline | Agent |
|---|---|---|---|
| timing | 7 | 57.1% | 100.0% |
| fx_difference | 11 | 90.9% | 90.9% |
| partial_payment | 12 | 91.7% | 100.0% |
| duplicate | 7 | 100.0% | 100.0% |
| transposition | 5 | 100.0% | 80.0% |
| missing_entry | 8 | 62.5% | 100.0% |
| **Overall** | **50** | **84.0%** | **96.0%** |
| Hard cases only | 13 | 38.5% | 100.0% |
| Labelled unclear | | 14.0% | 0.0% |

- **Lift:** +12.0 percentage points (agent minus rules)
- **Ungrounded notes:** 0 of 50 (a note citing a number no tool returned)
- **Cost:** $0.10 estimated, $0.0021 per exception, 3.3 tool calls on average
- **Stability:** 0 of 50 labels changed on a second run
- **Auto-match rate:** 94.04% of all ledger rows cleared by SQL before any exception reached the agent (5,000 synthetic transactions)

## Agent accuracy by stated confidence

| Confidence | n | Accuracy |
|---|---|---|
| high | 50 | 96.0% |
| medium | 0 | n/a |
| low | 0 | n/a |

## Confusion matrix: agent (rows = true type)

| true \ predicted | timing | fx | partial | dup | transp | missing | unclear |
|---|---|---|---|---|---|---|---|
| timing | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| fx_difference | 0 | 10 | 1 | 0 | 0 | 0 | 0 |
| partial_payment | 0 | 0 | 12 | 0 | 0 | 0 | 0 |
| duplicate | 0 | 0 | 0 | 7 | 0 | 0 | 0 |
| transposition | 0 | 1 | 0 | 0 | 4 | 0 | 0 |
| missing_entry | 0 | 0 | 0 | 0 | 0 | 8 | 0 |

## Confusion matrix: rules baseline (rows = true type)

| true \ predicted | timing | fx | partial | dup | transp | missing | unclear |
|---|---|---|---|---|---|---|---|
| timing | 4 | 0 | 0 | 0 | 0 | 0 | 3 |
| fx_difference | 0 | 10 | 0 | 0 | 0 | 0 | 1 |
| partial_payment | 0 | 1 | 11 | 0 | 0 | 0 | 0 |
| duplicate | 0 | 0 | 0 | 7 | 0 | 0 | 0 |
| transposition | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| missing_entry | 0 | 0 | 0 | 0 | 0 | 5 | 3 |

## Coverage

- Exceptions scored: 50
- Exceptions with no planted break behind them (excluded): 0
- Planted breaks that never surfaced as an exception: 0
