"""Phase 5 - Rules-only baseline: the if-then logic a finance team might build in Excel.

Run from the project folder:
    uv run python -m src.rules_baseline

The rules come from finance logic alone (see README, "Break taxonomy"). They were
written once and never tuned against the answer key. Rules are checked top to
bottom and the first one that fits wins. Writes data/predictions_baseline.csv.
"""
from __future__ import annotations

import calendar

import pandas as pd

from src.common import DATA, divisible_by_9, same_digits, write_csv

BANK_CODES = ("CHG", "FEE", "INT", "CHARGES")
FX_TOLERANCE = 0.02  # 2%
MONTH_END_DAYS = 5


def classify(exc: pd.Series, bank: pd.DataFrame, gl: pd.DataFrame) -> tuple[str, str]:
    """Return (label, rule that fired) for one exception."""
    b = bank.loc[exc["bank_id"]] if pd.notna(exc["bank_id"]) else None
    g = gl.loc[exc["gl_id"]] if pd.notna(exc["gl_id"]) else None

    if exc["kind"] == "amount_mismatch":
        bank_amt, gl_amt = float(b["amount_inr"]), float(g["amount_inr"])
        if divisible_by_9(bank_amt, gl_amt) and same_digits(bank_amt, gl_amt):
            return "transposition", "difference divisible by 9 and same digits"
        if g["currency"] != "INR" and abs(bank_amt - gl_amt) / abs(gl_amt) < FX_TOLERANCE:
            return "fx_difference", "foreign currency and difference under 2%"
        if abs(bank_amt) < abs(gl_amt):
            return "partial_payment", "bank amount smaller than GL amount"

    elif exc["kind"] == "gl_only":
        twins = gl[(gl["reference"] == g["reference"]) & (gl["amount_inr"] == g["amount_inr"])]
        if len(twins) > 1:
            return "duplicate", "another GL row has the same reference and amount"
        posted = pd.Timestamp(g["posting_date"])
        days_in_month = calendar.monthrange(posted.year, posted.month)[1]
        if posted.day > days_in_month - MONTH_END_DAYS:
            return "timing", "posted in the last 5 days of the month"

    elif exc["kind"] == "bank_only":
        if any(code in str(b["description"]).upper() for code in BANK_CODES):
            return "missing_entry", "bank description contains CHG, FEE, INT or CHARGES"

    return "unclear", "no rule fired"


def main() -> None:
    bank = pd.read_csv(DATA / "bank.csv", dtype={"reference": str}).set_index("bank_id", drop=False)
    gl = pd.read_csv(DATA / "gl.csv", dtype={"reference": str}).set_index("gl_id", drop=False)
    exceptions = pd.read_csv(DATA / "exceptions.csv")

    results = [classify(row, bank, gl) for _, row in exceptions.iterrows()]
    out = pd.DataFrame({
        "exception_id": exceptions["exception_id"],
        "predicted_type": [label for label, _ in results],
        "rule": [rule for _, rule in results],
    })
    write_csv(out, DATA / "predictions_baseline.csv")

    print(f"Labelled {len(out)} exceptions -> data/predictions_baseline.csv")
    print(out["predicted_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
