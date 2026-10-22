# 2 wrong agent answers (dev set)

For each: why did it go wrong? bad tool result / wrong reasoning / truly ambiguous.

## EXC-0048: true fx_difference (regular), agent said partial_payment

Confidence: high · forced unclear: None

Note: The GL records a USD payment of 7847.06 converted at 87.0341 rate, but the bank settled 672883.47 INR at an implied rate close to market rate. The difference is not due to FX rate but partial payment, as the bank amount is smaller than GL amount and no duplicate or transposition found.

Tool calls:
- `get_exception({"exception_id": "EXC-0048"})` -> `{"exception_id": "EXC-0048", "kind": "amount_mismatch", "kind_meaning": "Bank and GL rows share a reference but the amounts differ.", "bank_row": {"ledger": "bank", "bank_id": "B00760", "value_date": "2026-07-16", "amount_inr": 672883.47, "description": "SWIFT INW EVERGREEN MEDI", "reference": "EXP-956844", "status": "open exception EXC-0048 (amount_mismatch)"}, "gl_row": {"ledger": "gl", "gl_id":`
- `compare_amounts({"amount_a": 672883.47, "amount_b": 682961.8})` -> `{"amount_a": 672883.47, "amount_b": 682961.8, "difference_a_minus_b": -10078.33, "abs_difference": 10078.33, "pct_difference_of_b": 1.48, "a_as_pct_of_b": 98.52, "abs_a_smaller_than_abs_b": true, "difference_divisible_by_9": false, "same_digits": false}`
- `check_fx_explanation({"gl_id": "G00788"})` -> `{"gl_id": "G00788", "applicable": true, "currency": "USD", "amount_fx": 7847.06, "gl_fx_rate": 87.0341, "gl_amount_inr": 682961.8, "gl_amount_fx_times_gl_rate": 682961.8, "gl_inr_consistent_with_its_rate": true, "bank_id": "B00760", "settlement_date": "2026-07-16", "market_rate_on_settlement_date": 85.9592, "gl_amount_at_settlement_rate": 674527.0, "bank_amount_inr": 672883.47, "gap_bank_minus_gl"`
- `find_same_reference({"reference": "EXP-956844"})` -> `{"reference": "EXP-956844", "bank_count": 1, "gl_count": 1, "bank_rows": [{"ledger": "bank", "bank_id": "B00760", "value_date": "2026-07-16", "amount_inr": 672883.47, "description": "SWIFT INW EVERGREEN MEDI", "reference": "EXP-956844", "status": "open exception EXC-0048 (amount_mismatch)"}], "gl_rows": [{"ledger": "gl", "gl_id": "G00788", "posting_date": "2026-07-15", "amount_inr": 682961.8, "cur`

## EXC-0172: true transposition (regular), agent said fx_difference

Confidence: high · forced unclear: None

Note: The INR difference of 900 is explained by a foreign exchange rate difference. The bank's implied FX rate matches closely with the market rate, indicating the full foreign amount settled but at a slightly different rate than the GL rate.

Tool calls:
- `get_exception({"exception_id": "EXC-0172"})` -> `{"exception_id": "EXC-0172", "kind": "amount_mismatch", "kind_meaning": "Bank and GL rows share a reference but the amounts differ.", "bank_row": {"ledger": "bank", "bank_id": "B02454", "value_date": "2026-08-16", "amount_inr": -207609.51, "description": "SWIFT OUT CRESCENT IMPOR", "reference": "IMP-189487", "status": "open exception EXC-0172 (amount_mismatch)"}, "gl_row": {"ledger": "gl", "gl_id"`
- `compare_amounts({"amount_a": -207609.51, "amount_b": -206709.51})` -> `{"amount_a": -207609.51, "amount_b": -206709.51, "difference_a_minus_b": -900.0, "abs_difference": 900.0, "pct_difference_of_b": 0.44, "a_as_pct_of_b": 100.44, "abs_a_smaller_than_abs_b": false, "difference_divisible_by_9": true, "same_digits": true}`
- `check_fx_explanation({"gl_id": "G02490"})` -> `{"gl_id": "G02490", "applicable": true, "currency": "USD", "amount_fx": 2353.36, "gl_fx_rate": 88.2183, "gl_amount_inr": -206709.51, "gl_amount_fx_times_gl_rate": -207609.42, "gl_inr_consistent_with_its_rate": false, "bank_id": "B02454", "settlement_date": "2026-08-16", "market_rate_on_settlement_date": 87.9831, "gl_amount_at_settlement_rate": -207055.91, "bank_amount_inr": -207609.51, "gap_bank_m`
- `find_same_reference({"reference": "IMP-189487"})` -> `{"reference": "IMP-189487", "bank_count": 1, "gl_count": 1, "bank_rows": [{"ledger": "bank", "bank_id": "B02454", "value_date": "2026-08-16", "amount_inr": -207609.51, "description": "SWIFT OUT CRESCENT IMPOR", "reference": "IMP-189487", "status": "open exception EXC-0172 (amount_mismatch)"}], "gl_rows": [{"ledger": "gl", "gl_id": "G02490", "posting_date": "2026-08-16", "amount_inr": -206709.51, "`
