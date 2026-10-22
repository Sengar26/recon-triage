# LOG

Every number the project produces goes here the moment it appears, with the date. Newest at the bottom. The README and the resume only use numbers found in this file.

## 2026-09-25 · Phase 3: data generation

- Command: `uv run python -m src.generate_data`, seed 42.
- 5,000 genuine transactions dated 1 Jul to 30 Sep 2026; 15% in USD, the rest INR.
- `bank.csv` 5,000 rows, `gl.csv` 5,064 rows (64 duplicate postings), `fx_rates.csv` 193 days.
- 400 breaks planted, 118 of them deliberately hard:

| Break type | Planted | Hard | What makes the hard ones hard |
|---|---|---|---|
| timing | 68 | 22 | dated mid-September, not month-end |
| fx_difference | 68 | 20 | invoiced before the 14 Aug rupee drop, so the gap is over 2% |
| partial_payment | 66 | 28 | 95-99% paid; 17 of them in USD, so they look like FX |
| duplicate | 64 | 20 | second copy keyed with a slightly different reference |
| transposition | 66 | 0 | |
| missing_entry | 68 | 28 | vague bank text with no CHG / FEE / INT |

- Running the script twice produces byte-identical files.

## 2026-09-25 · Phase 4: deterministic matching

- Command: `uv run python -m src.match`. Both checks passed (every row accounted for exactly once; every matched pair has identical amounts).
- 10,064 rows in total. 4,732 pairs matched: 3,794 in pass 1 (reference + amount + date), 938 in pass 2 (amount + closest date, no reference).
- **Auto-match rate: 94.04%** of all ledger rows cleared by SQL (94.64% of bank rows).
- 400 exceptions: 200 amount_mismatch, 68 bank_only, 132 gl_only. Each traces to exactly one planted break; no planted break was missed and no exception lacks a planted break.
- Drift worth knowing: for 22 of the 64 duplicates, SQL matched the bank row to the second GL copy and left the original open. Either copy is equally "the duplicate", so the answer key lists both GL rows for each duplicate.
- Dev/test split (seed 42): 50 dev, 350 test. By chance the dev set holds no hard duplicates.

## 2026-09-25 · Phase 5: rules-only baseline

- Command: `uv run python -m src.rules_baseline`. Rules written once from the finance logic in the plan; never tuned against the answer key.
- Scored by `src/evaluate.py` on the 350-item test set:
  - **Overall accuracy: 76.6%**; hard cases only: 21.9% (105 items); labelled unclear: 22.0%.
  - Per type: timing 68.9%, fx_difference 75.4%, partial_payment 92.6%, duplicate 64.9%, transposition 100.0%, missing_entry 58.3%.
- Dev set (50 items), for reference only: 84.0%.

## 2026-09-25 · Phase 6: tools

- All six tools hand-checked against the raw CSVs on one exception of each break type (transposition, hard FX, hard USD partial, duplicate, hard timing, hard missing entry). Results agreed with the CSVs.

## 2026-09-25 · Phase 7: agent loop (offline test)

- Loop tested without the API using a scripted stand-in for the model (not part of the repo). Verified: tool dispatch, the 6-call cap forcing `unclear`, JSON and label validation, the grounding check (a fabricated "37.5 hours" was flagged), resume after interruption, the test-set run-once guard, and every API endpoint.
- Worth knowing: the scripted stand-in followed the same investigation steps as fixed code and labelled every test item correctly. On this synthetic data, most of the lift over the baseline comes from the tools (implied-rate check, same-reference and same-amount lookups), not from judgement that only a language model can supply.

## 2026-09-25 · Phase 7: dev-set tuning

- First real call (`--one EXC-0027`, a hard 97% USD partial): labelled partial_payment correctly from the bank's implied rate being 2.93% below market; note grounded; $0.0018.
- Dev run 1, model gpt-4.1-mini, 50 dev items: **agent 96.0% vs rules 84.0%**; hard cases 92.3% vs 38.5%; 1 ungrounded note; $0.09 ($0.0017 per exception); 3.2 tool calls on average. Every answer said "high" confidence, so confidence carried no information.
- The two wrong answers, both traced:
  1. EXC-0140, a transposition on a USD row, labelled fx_difference. **Bad tool result.** `check_fx_explanation` measured the rate effect as "GL foreign amount re-converted at today's rate minus the GL rupee amount", so a keying error in the rupee amount showed up as a 101% FX explanation. Fixed: the rate effect is now foreign amount × (settlement rate − GL rate), which gives 0.9% here. Added `gl_inr_consistent_with_its_rate`: on the dev set it is false only for the two USD transpositions and true for all 634 cleanly matched USD rows.
  2. EXC-0273, a hard 99% USD partial, labelled fx_difference. **Wrong reasoning.** The bank's implied rate was 1.16% below market; the tool description said "within 0.5% = FX, several percent below = partial", which left 1.16% in a gap. On the dev set every FX item sits within ±0.28% of market and every partial is at least 1.16% below. Tool description and prompt now say that more than 0.5% away from market means the full foreign amount did not settle.
- Prompt changes: check transposition first (divisible by 9 and same digits wins, even in USD); use "high" confidence only when every check agrees.
- Dev run 2 accidentally used the old code (the file update had not reached the laptop): 92.0%. It reproduced both errors above and added two new ones: on two duplicates the model answered with the exception kind "gl_only" instead of a break type, which the label check turned into "unclear". The same items were right in run 1, so this is run-to-run variation even at temperature 0. Prompt now states that the exception kind is never a break type.
- Dev run 3 (fixed code): **96.0% vs rules 84.0%**; hard cases 13 of 13; 0 ungrounded notes; $0.09. Transposition and partial payments now all correct. Two errors left, both duplicates, and both are the Phase 4 drift cases where SQL matched the bank row to the second GL copy and left the original open. The agent answered "gl_only" on one and called the other timing, even though `find_same_reference` showed two GL rows and one bank row. Changes: the prompt now says the open copy is the duplicate whichever copy the bank matched, and the code gives the model one chance to correct a label that is not allowed (reported as "labels repaired").
- Dev runs 4 and 5 (final prompt, identical code, run twice): **96.0% vs rules 84.0%**; hard cases 13 of 13; 0 ungrounded notes; **stability: 0 of 50 labels changed** between the two runs; $0.10 per run. The duplicates are fixed, but two items that were right in run 3 went wrong: EXC-0048 (an FX difference called partial_payment, although the agent's own note says the implied rate is close to market) and EXC-0172 (a USD transposition called fx_difference, although divisible-by-9, same digits and the GL-consistency flag all pointed to transposition). Both are wrong reasoning over correct tool results. Each prompt change fixed some items and broke others, so tuning stopped here rather than fitting the prompt to 50 items. The test set is run once with this prompt.
- Stated confidence was "high" on all 50 answers in every dev run, so it does not separate right answers from wrong ones and is not a usable signal for routing items to a human.

## Agent runs

- Model: gpt-4.1-mini, temperature 0.
- Estimated API spend (from token counts): about $0.45 across the five dev runs, $0.78 for the test run.
- Actual spend (from the OpenAI usage page):

<!-- `uv run python -m src.evaluate --log` appends dated results below. -->

## 2026-09-25 · evaluation, test set

- Seed 42; model gpt-4.1-mini
- Exceptions scored (M): 350, of which hard: 105
- Rules baseline accuracy (Z): 76.6%; hard cases 21.9%
- Agent accuracy (Y): 92.9%; hard cases 83.8%
- Lift: +16.3 pp
- Agent unclear rate: 0.0%; ungrounded notes: 0; forced unclear: 0; labels repaired: 0
- Estimated cost: $0.77 ($0.0022 per exception)
- Per type (rules / agent): timing 68.9% / 100.0%; fx_difference 75.4% / 94.7%; partial_payment 92.6% / 98.1%; duplicate 64.9% / 68.4%; transposition 100.0% / 98.4%; missing_entry 58.3% / 96.7%
- Incomplete run: 5 test items (EXC-0227, EXC-0241, EXC-0245, EXC-0275, EXC-0291) got no answer because their API calls failed during the run, and this evaluation counted them as wrong. They were completed by resuming the same run with the unchanged prompt. The next entry is the final result.

## 2026-09-25 · evaluation, test set

- Seed 42; model gpt-4.1-mini
- Exceptions scored (M): 350, of which hard: 105
- Rules baseline accuracy (Z): 76.6%; hard cases 21.9%
- Agent accuracy (Y): 94.3%; hard cases 84.8%
- Lift: +17.7 pp
- Agent unclear rate: 0.0%; ungrounded notes: 0; forced unclear: 0; labels repaired: 0
- Estimated cost: $0.78 ($0.0022 per exception)
- Per type (rules / agent): timing 68.9% / 100.0%; fx_difference 75.4% / 96.5%; partial_payment 92.6% / 100.0%; duplicate 64.9% / 70.2%; transposition 100.0% / 98.4%; missing_entry 58.3% / 100.0%
- The 20 wrong answers: 17 duplicates (13 called timing, 4 called missing_entry), 2 FX differences called partial_payment, 1 transposition called partial_payment. Stated confidence was "high" on 348 of 350 answers.

## Error analysis

These are the ten wrong answers listed in `results/errors_test.md`. In all ten, the tool results were correct: **0 bad tool results, 10 wrong reasoning, 0 truly ambiguous.**

1. EXC-0038, hard duplicate, called timing. The agent's own bank search found the payment for the same amount from the same customer under INV-520214 (this row says INV-520124, two digits swapped), already matched to another GL row. It did not take the last step: that other GL row is the twin, so this one is the duplicate. Wrong reasoning.
2. EXC-0040, hard duplicate, called missing_entry. Same pattern (PO-984820 vs PO-894820). missing_entry is impossible for a GL-only item by the taxonomy. Wrong reasoning.
3. EXC-0123, hard duplicate, called timing. Same pattern (PO-311523 vs PO-311532). Wrong reasoning.
4. EXC-0132, hard duplicate, called missing_entry. Same pattern (BILL-700030 vs BILL-700003), and again a label the taxonomy rules out for a GL-only item. Wrong reasoning.
5. EXC-0164, hard duplicate, called timing. The second copy was keyed without its prefix (680420 vs INV-680420); the note even calls it "a related reference". Wrong reasoning.
6. EXC-0182, hard duplicate, called timing. Same pattern (EXP-728394 vs EXP-782394). Wrong reasoning.
7. EXC-0256, regular duplicate, called timing. find_same_reference showed two GL rows and one bank row matched to the other copy, the exact case the prompt covers (the original left open while the copy was matched). Instruction not followed. Wrong reasoning.
8. EXC-0307, FX difference, called partial_payment. The bank amount was 100.3% of the GL amount (a larger outflow), yet the note says the bank paid less: it misread the sign of a negative amount. Wrong reasoning.
9. EXC-0316, hard duplicate, called timing. Same re-keyed pattern (IMP-227217 vs IMP-227271). Wrong reasoning.
10. EXC-0321, FX difference, called partial_payment (medium confidence). The note says the implied rate is close to market and then concludes the full amount did not settle, the opposite of the rule. Wrong reasoning.

Takeaway: the tools surfaced the right evidence every time. The main weakness is the re-keyed duplicate, which needs one more hop (GL row -> bank row under a near-identical reference -> the GL row that bank row is matched to). A tool that looks for same-amount, same-counterparty GL twins directly would likely fix most of these. It was not added, because changing the system after seeing test results would make the test score meaningless.
