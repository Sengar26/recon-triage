# 10 wrong agent answers (test set)

For each: why did it go wrong? bad tool result / wrong reasoning / truly ambiguous.

## EXC-0038: true duplicate (hard), agent said timing

Confidence: high · forced unclear: None

Note: The GL entry is likely a deposit in transit or outstanding cheque since it is recorded in the GL but not yet reflected in the bank statement by the statement date. The timing gap and lack of exact bank reference match support this conclusion.

Tool calls:
- `get_exception({"exception_id": "EXC-0038"})` -> `{"exception_id": "EXC-0038", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G00635", "posting_date": "2026-07-13", "amount_inr": 35739.5, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Lotus Foods Ltd", "reference": "INV-520124", "status": "open exception EXC-0038 (gl_only)"}}`
- `find_same_reference({"reference": "INV-520124"})` -> `{"reference": "INV-520124", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G00635", "posting_date": "2026-07-13", "amount_inr": 35739.5, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Lotus Foods Ltd", "reference": "INV-520124", "status": "open exception EXC-0038 (gl_only)"}]}`
- `days_to_period_end({"date": "2026-07-13"})` -> `{"date": "2026-07-13", "month_end": "2026-07-31", "days_to_month_end": 18, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 79}`
- `search_other_ledger({"ledger": "bank", "amount": 35739.5, "date": "2026-07-13", "day_window": 10, "pct_tolerance": 0})` -> `{"searched_ledger": "bank", "amount": 35739.5, "date": "2026-07-13", "day_window": 10, "pct_tolerance": 0, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B00657", "value_date": "2026-07-14", "amount_inr": 35739.5, "description": "NEFT CR LOTUS FOODS LTD", "reference": "INV-520214", "status": "matched to G00605 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date": 1}]`

## EXC-0040: true duplicate (hard), agent said missing_entry

Confidence: high · forced unclear: None

Note: The GL entry for -7522.57 INR dated 2026-07-13 with reference PO-894820 has no corresponding bank transaction and no duplicate GL entry. The similar bank transaction found has a different reference and is matched to another GL entry. This indicates the bank has not recorded this transaction, classifying it as a missing entry.

Tool calls:
- `get_exception({"exception_id": "EXC-0040"})` -> `{"exception_id": "EXC-0040", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G00654", "posting_date": "2026-07-13", "amount_inr": -7522.57, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Kaveri Electricals LLP", "reference": "PO-894820", "status": "open exception EXC-0040 (gl_only)"}}`
- `find_same_reference({"reference": "PO-894820"})` -> `{"reference": "PO-894820", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G00654", "posting_date": "2026-07-13", "amount_inr": -7522.57, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Kaveri Electricals LLP", "reference": "PO-894820", "status": "open exception EXC-0040 (gl_only)"}]}`
- `days_to_period_end({"date": "2026-07-13"})` -> `{"date": "2026-07-13", "month_end": "2026-07-31", "days_to_month_end": 18, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 79}`
- `search_other_ledger({"ledger": "bank", "amount": -7522.57, "date": "2026-07-13", "day_window": 5, "pct_tolerance": 1})` -> `{"searched_ledger": "bank", "amount": -7522.57, "date": "2026-07-13", "day_window": 5, "pct_tolerance": 1, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B00408", "value_date": "2026-07-09", "amount_inr": -7522.57, "description": "NEFT DR KAVERI ELECTRICA", "reference": "PO-984820", "status": "matched to G00413 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date": -4`

## EXC-0123: true duplicate (hard), agent said timing

Confidence: high · forced unclear: None

Note: The GL entry is not yet reflected in the bank statement by the statement date, likely an outstanding cheque or payment in transit. The bank has a similar amount but different reference, confirming the GL entry is timing-related.

Tool calls:
- `get_exception({"exception_id": "EXC-0123"})` -> `{"exception_id": "EXC-0123", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G01939", "posting_date": "2026-08-06", "amount_inr": -69916.85, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Royal Enterprises Ltd", "reference": "PO-311532", "status": "open exception EXC-0123 (gl_only)"}}`
- `find_same_reference({"reference": "PO-311532"})` -> `{"reference": "PO-311532", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G01939", "posting_date": "2026-08-06", "amount_inr": -69916.85, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Royal Enterprises Ltd", "reference": "PO-311532", "status": "open exception EXC-0123 (gl_only)"}]}`
- `days_to_period_end({"date": "2026-08-06"})` -> `{"date": "2026-08-06", "month_end": "2026-08-31", "days_to_month_end": 25, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 55}`
- `search_other_ledger({"ledger": "bank", "amount": -69916.85, "date": "2026-08-06", "day_window": 10, "pct_tolerance": 0})` -> `{"searched_ledger": "bank", "amount": -69916.85, "date": "2026-08-06", "day_window": 10, "pct_tolerance": 0, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B01739", "value_date": "2026-08-03", "amount_inr": -69916.85, "description": "CHQ PAID 623769", "reference": "PO-311523", "status": "matched to G01687 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date": -3}]}`

## EXC-0132: true duplicate (hard), agent said missing_entry

Confidence: high · forced unclear: None

Note: The GL entry for -116008.82 INR on 2026-08-08 with reference BILL-700003 has no corresponding bank transaction. There is no duplicate GL entry or matching bank entry with the same reference. The timing gap is large, and the bank entry with a similar amount is matched to a different GL entry, indicating this is a missing entry in the bank ledger, likely an unrecorded bank transaction.

Tool calls:
- `get_exception({"exception_id": "EXC-0132"})` -> `{"exception_id": "EXC-0132", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G02081", "posting_date": "2026-08-08", "amount_inr": -116008.82, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Metro Pharma LLP", "reference": "BILL-700003", "status": "open exception EXC-0132 (gl_only)"}}`
- `find_same_reference({"reference": "BILL-700003"})` -> `{"reference": "BILL-700003", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G02081", "posting_date": "2026-08-08", "amount_inr": -116008.82, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Metro Pharma LLP", "reference": "BILL-700003", "status": "open exception EXC-0132 (gl_only)"}]}`
- `days_to_period_end({"date": "2026-08-08"})` -> `{"date": "2026-08-08", "month_end": "2026-08-31", "days_to_month_end": 23, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 53}`
- `search_other_ledger({"ledger": "bank", "amount": -116008.82, "date": "2026-08-08", "day_window": 5, "pct_tolerance": 0})` -> `{"searched_ledger": "bank", "amount": -116008.82, "date": "2026-08-08", "day_window": 5, "pct_tolerance": 0, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B01760", "value_date": "2026-08-03", "amount_inr": -116008.82, "description": "NEFT DR METRO PHARMA LLP", "reference": "BILL-700030", "status": "matched to G01797 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_dat`

## EXC-0164: true duplicate (hard), agent said timing

Confidence: high · forced unclear: None

Note: The GL entry for 7696.07 INR on 2026-08-14 is not yet reflected in the bank statement but a similar bank entry exists dated 2026-08-11 with a related reference. The timing and reference pattern indicate this is a timing difference, likely a deposit in transit or outstanding cheque.

Tool calls:
- `get_exception({"exception_id": "EXC-0164"})` -> `{"exception_id": "EXC-0164", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G02365", "posting_date": "2026-08-14", "amount_inr": 7696.07, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Krishna Electricals LLP", "reference": "680420", "status": "open exception EXC-0164 (gl_only)"}}`
- `find_same_reference({"reference": "680420"})` -> `{"reference": "680420", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G02365", "posting_date": "2026-08-14", "amount_inr": 7696.07, "currency": "INR", "amount_fx": null, "fx_rate": null, "counterparty": "Krishna Electricals LLP", "reference": "680420", "status": "open exception EXC-0164 (gl_only)"}]}`
- `search_other_ledger({"ledger": "bank", "amount": 7696.07, "date": "2026-08-14", "day_window": 5, "pct_tolerance": 1})` -> `{"searched_ledger": "bank", "amount": 7696.07, "date": "2026-08-14", "day_window": 5, "pct_tolerance": 1, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B02172", "value_date": "2026-08-11", "amount_inr": 7696.07, "description": "NEFT CR KRISHNA ELECTRIC", "reference": "INV-680420", "status": "matched to G02233 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date": -3}`
- `days_to_period_end({"date": "2026-08-14"})` -> `{"date": "2026-08-14", "month_end": "2026-08-31", "days_to_month_end": 17, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 47}`

## EXC-0182: true duplicate (hard), agent said timing

Confidence: high · forced unclear: None

Note: The GL entry is a foreign currency payment recorded on 2026-08-19 with no matching bank entry by the statement date. A bank entry with the same amount but a different reference exists earlier, indicating the GL entry is likely a timing difference, not yet cleared by the bank statement date.

Tool calls:
- `get_exception({"exception_id": "EXC-0182"})` -> `{"exception_id": "EXC-0182", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G02689", "posting_date": "2026-08-19", "amount_inr": 57608.38, "currency": "USD", "amount_fx": 656.59, "fx_rate": 87.7387, "counterparty": "Evergreen Medical Inc", "reference": "EXP-782394", "status": "open exception EXC-0182 (gl_only)"}}`
- `find_same_reference({"reference": "EXP-782394"})` -> `{"reference": "EXP-782394", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G02689", "posting_date": "2026-08-19", "amount_inr": 57608.38, "currency": "USD", "amount_fx": 656.59, "fx_rate": 87.7387, "counterparty": "Evergreen Medical Inc", "reference": "EXP-782394", "status": "open exception EXC-0182 (gl_only)"}]}`
- `check_fx_explanation({"gl_id": "G02689"})` -> `{"gl_id": "G02689", "applicable": false, "reason": "No bank row found for this GL row, so there is no settlement to compare."}`
- `days_to_period_end({"date": "2026-08-19"})` -> `{"date": "2026-08-19", "month_end": "2026-08-31", "days_to_month_end": 12, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 42}`
- `search_other_ledger({"ledger": "bank", "amount": 57608.38, "date": "2026-08-19", "day_window": 5, "pct_tolerance": 1})` -> `{"searched_ledger": "bank", "amount": 57608.38, "date": "2026-08-19", "day_window": 5, "pct_tolerance": 1, "candidate_count": 1, "candidates": [{"ledger": "bank", "bank_id": "B02437", "value_date": "2026-08-16", "amount_inr": 57608.38, "description": "SWIFT INW EVERGREEN MEDI", "reference": "EXP-728394", "status": "matched to G02541 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date": -`

## EXC-0256: true duplicate (regular), agent said timing

Confidence: high · forced unclear: None

Note: The open GL entry dated 2026-09-10 for 647573.15 INR in USD has a matching bank entry one day later, indicating a timing difference. The FX rates are consistent and the full foreign amount settled, so this is an outstanding GL item not yet cleared by the bank at statement date.

Tool calls:
- `get_exception({"exception_id": "EXC-0256"})` -> `{"exception_id": "EXC-0256", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G03822", "posting_date": "2026-09-10", "amount_inr": 647573.15, "currency": "USD", "amount_fx": 7369.49, "fx_rate": 87.8722, "counterparty": "Lakeside Paper Co", "reference": "EXP-691764", "status": "open exception EXC-0256 (gl_only)"}}`
- `find_same_reference({"reference": "EXP-691764"})` -> `{"reference": "EXP-691764", "bank_count": 1, "gl_count": 2, "bank_rows": [{"ledger": "bank", "bank_id": "B03829", "value_date": "2026-09-11", "amount_inr": 647573.15, "description": "SWIFT INW LAKESIDE PAPER", "reference": "EXP-691764", "status": "matched to G03906 (pass 1)"}], "gl_rows": [{"ledger": "gl", "gl_id": "G03822", "posting_date": "2026-09-10", "amount_inr": 647573.15, "currency": "USD",`
- `check_fx_explanation({"gl_id": "G03822"})` -> `{"gl_id": "G03822", "applicable": true, "currency": "USD", "amount_fx": 7369.49, "gl_fx_rate": 87.8722, "gl_amount_inr": 647573.15, "gl_amount_fx_times_gl_rate": 647573.3, "gl_inr_consistent_with_its_rate": true, "bank_id": "B03829", "settlement_date": "2026-09-11", "market_rate_on_settlement_date": 87.9577, "gl_amount_at_settlement_rate": 648203.39, "bank_amount_inr": 647573.15, "gap_bank_minus_g`

## EXC-0307: true fx_difference (regular), agent said partial_payment

Confidence: high · forced unclear: None

Note: The bank amount is smaller than the GL amount and the difference is not explained by FX rate differences or transposition. The foreign currency amount fully settled at a rate close to market, but the bank paid less than the GL amount, indicating a partial payment.

Tool calls:
- `get_exception({"exception_id": "EXC-0307"})` -> `{"exception_id": "EXC-0307", "kind": "amount_mismatch", "kind_meaning": "Bank and GL rows share a reference but the amounts differ.", "bank_row": {"ledger": "bank", "bank_id": "B04360", "value_date": "2026-09-21", "amount_inr": -109978.0, "description": "SWIFT OUT SUMMIT APPAREL", "reference": "IMP-550838", "status": "open exception EXC-0307 (amount_mismatch)"}, "gl_row": {"ledger": "gl", "gl_id":`
- `compare_amounts({"amount_a": -109978.0, "amount_b": -109654.21})` -> `{"amount_a": -109978.0, "amount_b": -109654.21, "difference_a_minus_b": -323.79, "abs_difference": 323.79, "pct_difference_of_b": 0.3, "a_as_pct_of_b": 100.3, "abs_a_smaller_than_abs_b": false, "difference_divisible_by_9": false, "same_digits": false}`
- `check_fx_explanation({"gl_id": "G04409"})` -> `{"gl_id": "G04409", "applicable": true, "currency": "USD", "amount_fx": 1249.0, "gl_fx_rate": 87.7936, "gl_amount_inr": -109654.21, "gl_amount_fx_times_gl_rate": -109654.21, "gl_inr_consistent_with_its_rate": true, "bank_id": "B04360", "settlement_date": "2026-09-21", "market_rate_on_settlement_date": 87.8696, "gl_amount_at_settlement_rate": -109749.13, "bank_amount_inr": -109978.0, "gap_bank_minu`

## EXC-0316: true duplicate (hard), agent said timing

Confidence: high · forced unclear: None

Note: The GL entry for -74612.52 INR dated 2026-09-22 has no matching bank transaction by the statement date 2026-09-30. Given it is 8 days before month end and no bank counterpart exists, this is likely a timing difference (outstanding payment not yet cleared by bank).

Tool calls:
- `get_exception({"exception_id": "EXC-0316"})` -> `{"exception_id": "EXC-0316", "kind": "gl_only", "kind_meaning": "In the GL; no bank row matched it.", "bank_row": null, "gl_row": {"ledger": "gl", "gl_id": "G04497", "posting_date": "2026-09-22", "amount_inr": -74612.52, "currency": "USD", "amount_fx": 847.76, "fx_rate": 88.0114, "counterparty": "Falcon Aero Parts Inc", "reference": "IMP-227271", "status": "open exception EXC-0316 (gl_only)"}}`
- `find_same_reference({"reference": "IMP-227271"})` -> `{"reference": "IMP-227271", "bank_count": 0, "gl_count": 1, "bank_rows": [], "gl_rows": [{"ledger": "gl", "gl_id": "G04497", "posting_date": "2026-09-22", "amount_inr": -74612.52, "currency": "USD", "amount_fx": 847.76, "fx_rate": 88.0114, "counterparty": "Falcon Aero Parts Inc", "reference": "IMP-227271", "status": "open exception EXC-0316 (gl_only)"}]}`
- `check_fx_explanation({"gl_id": "G04497"})` -> `{"gl_id": "G04497", "applicable": false, "reason": "No bank row found for this GL row, so there is no settlement to compare."}`
- `days_to_period_end({"date": "2026-09-22"})` -> `{"date": "2026-09-22", "month_end": "2026-09-30", "days_to_month_end": 8, "in_last_5_days_of_month": false, "statement_period_end": "2026-09-30", "days_to_statement_end": 8}`
- `search_other_ledger({"ledger": "bank", "amount": -74612.52, "date": "2026-09-22", "day_window": 5, "pct_tolerance": 1})` -> `{"searched_ledger": "bank", "amount": -74612.52, "date": "2026-09-22", "day_window": 5, "pct_tolerance": 1, "candidate_count": 6, "candidates": [{"ledger": "bank", "bank_id": "B04393", "value_date": "2026-09-21", "amount_inr": -74612.52, "description": "SWIFT OUT FALCON AERO PA", "reference": "IMP-227217", "status": "matched to G04388 (pass 1)", "pct_difference_from_amount": 0.0, "days_from_date":`

## EXC-0321: true fx_difference (regular), agent said partial_payment

Confidence: medium · forced unclear: None

Note: The exception is a foreign currency payment with a small amount difference. The bank implied FX rate is close to market rate, so the full foreign amount likely did not settle. The bank amount is smaller than the GL amount and the gap is only partially explained by FX rate change, indicating a partial payment rather than a timing or FX difference.

Tool calls:
- `get_exception({"exception_id": "EXC-0321"})` -> `{"exception_id": "EXC-0321", "kind": "amount_mismatch", "kind_meaning": "Bank and GL rows share a reference but the amounts differ.", "bank_row": {"ledger": "bank", "bank_id": "B04560", "value_date": "2026-09-24", "amount_inr": 108365.55, "description": "SWIFT INW CRESCENT IMPOR", "reference": "EXP-987902", "status": "open exception EXC-0321 (amount_mismatch)"}, "gl_row": {"ledger": "gl", "gl_id":`
- `compare_amounts({"amount_a": 108365.55, "amount_b": 108829.79})` -> `{"amount_a": 108365.55, "amount_b": 108829.79, "difference_a_minus_b": -464.24, "abs_difference": 464.24, "pct_difference_of_b": 0.43, "a_as_pct_of_b": 99.57, "abs_a_smaller_than_abs_b": true, "difference_divisible_by_9": false, "same_digits": false}`
- `check_fx_explanation({"gl_id": "G04581"})` -> `{"gl_id": "G04581", "applicable": true, "currency": "USD", "amount_fx": 1234.92, "gl_fx_rate": 88.127, "gl_amount_inr": 108829.79, "gl_amount_fx_times_gl_rate": 108829.79, "gl_inr_consistent_with_its_rate": true, "bank_id": "B04560", "settlement_date": "2026-09-24", "market_rate_on_settlement_date": 87.9578, "gl_amount_at_settlement_rate": 108620.85, "bank_amount_inr": 108365.55, "gap_bank_minus_g`
- `find_same_reference({"reference": "EXP-987902"})` -> `{"reference": "EXP-987902", "bank_count": 1, "gl_count": 1, "bank_rows": [{"ledger": "bank", "bank_id": "B04560", "value_date": "2026-09-24", "amount_inr": 108365.55, "description": "SWIFT INW CRESCENT IMPOR", "reference": "EXP-987902", "status": "open exception EXC-0321 (amount_mismatch)"}], "gl_rows": [{"ledger": "gl", "gl_id": "G04581", "posting_date": "2026-09-23", "amount_inr": 108829.79, "cu`
