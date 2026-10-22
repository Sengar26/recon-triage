"""Phase 6 - The tools the agent is allowed to call.

Each tool is an ordinary Python function that returns a plain dictionary. The
language model never sees the CSV files and never does arithmetic: it asks for
a tool by name, this file runs it, and the result goes back to the model.

None of these functions read data/answer_key.csv.

Try one by hand from the project folder:
    uv run python -m src.tools EXC-0001
"""
from __future__ import annotations

import calendar
import json
import sys
from functools import lru_cache

import pandas as pd

from src.common import DATA, PERIOD_END, divisible_by_9, same_digits

KIND_MEANING = {
    "amount_mismatch": "Bank and GL rows share a reference but the amounts differ.",
    "bank_only": "In the bank statement; no GL row matched it.",
    "gl_only": "In the GL; no bank row matched it.",
}


# ---------------------------------------------------------------- data access

@lru_cache(maxsize=1)
def _data() -> dict:
    """Load the ledgers once and note each row's matching status."""
    bank = pd.read_csv(DATA / "bank.csv", dtype={"reference": str})
    gl = pd.read_csv(DATA / "gl.csv", dtype={"reference": str})
    fx = pd.read_csv(DATA / "fx_rates.csv")
    exceptions = pd.read_csv(DATA / "exceptions.csv")
    matched = pd.read_csv(DATA / "matched.csv")

    status: dict[str, str] = {}
    for bank_id, gl_id, pass_no in zip(matched["bank_id"], matched["gl_id"], matched["pass"]):
        status[bank_id] = f"matched to {gl_id} (pass {pass_no})"
        status[gl_id] = f"matched to {bank_id} (pass {pass_no})"
    for r in exceptions.itertuples():
        for row_id in (r.bank_id, r.gl_id):
            if isinstance(row_id, str):
                status[row_id] = f"open exception {r.exception_id} ({r.kind})"

    return {
        "bank": bank.set_index("bank_id", drop=False),
        "gl": gl.set_index("gl_id", drop=False),
        "fx": pd.Series(fx["usd_inr"].to_numpy(), index=pd.to_datetime(fx["date"])),
        "exceptions": exceptions.set_index("exception_id", drop=False),
        "matched": matched,
        "status": status,
    }


def _clean(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "item"):  # numpy number -> plain Python number
        return value.item()
    return value


def _bank_row(bank_id: str) -> dict:
    r = _data()["bank"].loc[bank_id]
    return {"ledger": "bank", "bank_id": bank_id, "value_date": r["value_date"],
            "amount_inr": _clean(r["amount_inr"]), "description": r["description"],
            "reference": _clean(r["reference"]), "status": _data()["status"].get(bank_id)}


def _gl_row(gl_id: str) -> dict:
    r = _data()["gl"].loc[gl_id]
    return {"ledger": "gl", "gl_id": gl_id, "posting_date": r["posting_date"],
            "amount_inr": _clean(r["amount_inr"]), "currency": r["currency"],
            "amount_fx": _clean(r["amount_fx"]), "fx_rate": _clean(r["fx_rate"]),
            "counterparty": r["counterparty"], "reference": _clean(r["reference"]),
            "status": _data()["status"].get(gl_id)}


# ---------------------------------------------------------------- the six tools

def get_exception(exception_id: str) -> dict:
    exc = _data()["exceptions"]
    if exception_id not in exc.index:
        return {"error": f"No exception with id {exception_id}."}
    e = exc.loc[exception_id]
    return {
        "exception_id": exception_id,
        "kind": e["kind"],
        "kind_meaning": KIND_MEANING[e["kind"]],
        "bank_row": _bank_row(e["bank_id"]) if isinstance(e["bank_id"], str) else None,
        "gl_row": _gl_row(e["gl_id"]) if isinstance(e["gl_id"], str) else None,
    }


def find_same_reference(reference: str) -> dict:
    d = _data()
    bank_ids = d["bank"].index[d["bank"]["reference"] == reference].tolist()
    gl_ids = d["gl"].index[d["gl"]["reference"] == reference].tolist()
    return {
        "reference": reference,
        "bank_count": len(bank_ids),
        "gl_count": len(gl_ids),
        "bank_rows": [_bank_row(i) for i in bank_ids],
        "gl_rows": [_gl_row(i) for i in gl_ids],
    }


def search_other_ledger(ledger: str, amount: float, date: str,
                        day_window: int = 5, pct_tolerance: float = 1.0) -> dict:
    d = _data()
    if ledger not in ("bank", "gl"):
        return {"error": "ledger must be 'bank' or 'gl' (the ledger to search in)."}
    if amount == 0:
        return {"error": "amount must not be zero."}
    table = d[ledger]
    date_col = "value_date" if ledger == "bank" else "posting_date"
    target = pd.Timestamp(date)
    gap_days = (pd.to_datetime(table[date_col]) - target).dt.days
    pct_off = (table["amount_inr"] - amount).abs() / abs(amount) * 100
    same_direction = (table["amount_inr"] > 0) == (amount > 0)
    hits = table[same_direction & (gap_days.abs() <= day_window) & (pct_off <= pct_tolerance)].copy()
    hits["_pct"] = pct_off[hits.index]
    hits["_gap"] = gap_days[hits.index]
    hits = hits.sort_values(["_pct", "_gap"]).head(10)

    candidates = []
    for row_id, h in hits.iterrows():
        row = _bank_row(row_id) if ledger == "bank" else _gl_row(row_id)
        row["pct_difference_from_amount"] = round(float(h["_pct"]), 2)
        row["days_from_date"] = int(h["_gap"])
        candidates.append(row)
    return {
        "searched_ledger": ledger,
        "amount": amount, "date": date,
        "day_window": day_window, "pct_tolerance": pct_tolerance,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def compare_amounts(amount_a: float, amount_b: float) -> dict:
    a, b = float(amount_a), float(amount_b)
    if b == 0:
        return {"error": "amount_b must not be zero."}
    diff = round(a - b, 2)
    return {
        "amount_a": a,
        "amount_b": b,
        "difference_a_minus_b": diff,
        "abs_difference": abs(diff),
        "pct_difference_of_b": round(abs(diff) / abs(b) * 100, 2),
        "a_as_pct_of_b": round(abs(a) / abs(b) * 100, 2),
        "abs_a_smaller_than_abs_b": abs(a) < abs(b),
        "difference_divisible_by_9": divisible_by_9(a, b),
        "same_digits": same_digits(a, b),
    }


def check_fx_explanation(gl_id: str) -> dict:
    d = _data()
    if gl_id not in d["gl"].index:
        return {"error": f"No GL row with id {gl_id}."}
    g = d["gl"].loc[gl_id]
    if g["currency"] == "INR":
        return {"gl_id": gl_id, "applicable": False,
                "reason": "The GL row is in INR, so no currency conversion is involved."}

    # Find the bank row this GL row settled against.
    exc = d["exceptions"]
    paired = exc[(exc["gl_id"] == gl_id) & exc["bank_id"].notna()]
    matched = d["matched"][d["matched"]["gl_id"] == gl_id]
    if len(paired):
        bank_id = paired.iloc[0]["bank_id"]
    elif len(matched):
        bank_id = matched.iloc[0]["bank_id"]
    else:
        same_ref = d["bank"][d["bank"]["reference"] == g["reference"]]
        if same_ref.empty:
            return {"gl_id": gl_id, "applicable": False,
                    "reason": "No bank row found for this GL row, so there is no settlement to compare."}
        bank_id = same_ref.index[0]
    b = d["bank"].loc[bank_id]

    settlement = pd.Timestamp(b["value_date"])
    market_rate = float(d["fx"][:settlement].iloc[-1])
    sign = 1.0 if g["amount_inr"] > 0 else -1.0
    gl_amount = float(g["amount_inr"])
    bank_amount = float(b["amount_inr"])
    amount_fx, gl_rate = float(g["amount_fx"]), float(g["fx_rate"])
    at_settlement = round(sign * amount_fx * market_rate, 2)
    gap = round(bank_amount - gl_amount, 2)
    # The part of the gap a rate change can explain: foreign amount x (settlement rate - GL rate).
    explained = round(sign * amount_fx * (market_rate - gl_rate), 2)
    implied_rate = abs(bank_amount) / amount_fx
    # Was the GL rupee amount keyed consistently with its own foreign amount and rate?
    gl_recomputed = round(sign * amount_fx * gl_rate, 2)
    return {
        "gl_id": gl_id,
        "applicable": True,
        "currency": g["currency"],
        "amount_fx": amount_fx,
        "gl_fx_rate": gl_rate,
        "gl_amount_inr": gl_amount,
        "gl_amount_fx_times_gl_rate": gl_recomputed,
        "gl_inr_consistent_with_its_rate": abs(gl_recomputed - gl_amount) <= max(1.0, abs(gl_amount) * 0.0005),
        "bank_id": bank_id,
        "settlement_date": b["value_date"],
        "market_rate_on_settlement_date": market_rate,
        "gl_amount_at_settlement_rate": at_settlement,
        "bank_amount_inr": bank_amount,
        "gap_bank_minus_gl": gap,
        "gap_explained_by_rate_change": explained,
        "share_of_gap_explained_pct": round(explained / gap * 100, 1) if gap else None,
        "bank_implied_rate": round(implied_rate, 4),
        "bank_implied_rate_vs_market_pct": round((implied_rate - market_rate) / market_rate * 100, 2),
    }


def days_to_period_end(date: str) -> dict:
    t = pd.Timestamp(date)
    month_end = t.replace(day=calendar.monthrange(t.year, t.month)[1])
    statement_end = pd.Timestamp(PERIOD_END)
    return {
        "date": date,
        "month_end": month_end.strftime("%Y-%m-%d"),
        "days_to_month_end": (month_end - t).days,
        "in_last_5_days_of_month": (month_end - t).days < 5,
        "statement_period_end": PERIOD_END,
        "days_to_statement_end": (statement_end - t).days,
    }


# ---------------------------------------------------------------- tool menu for the model
# The model picks tools by reading these descriptions, so they are written as
# instructions to a new colleague.

TOOLS = [
    {"type": "function", "function": {
        "name": "get_exception",
        "description": (
            "Start here. Returns the open reconciliation exception: its kind "
            "(amount_mismatch, bank_only or gl_only) and every field of the bank row "
            "and/or GL row involved. Amounts are in INR, signed from the company's "
            "view: positive = money in, negative = money out."),
        "parameters": {"type": "object", "properties": {
            "exception_id": {"type": "string", "description": "e.g. EXC-0042"}},
            "required": ["exception_id"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "find_same_reference",
        "description": (
            "Lists every row in BOTH ledgers carrying this reference number, with each "
            "row's status (matched to which row, or which open exception). Use it to "
            "spot a GL entry keyed twice (two GL rows, same reference and amount, only "
            "one bank row) or to see the full story behind a reference."),
        "parameters": {"type": "object", "properties": {
            "reference": {"type": "string", "description": "e.g. INV-123456"}},
            "required": ["reference"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "search_other_ledger",
        "description": (
            "Looks for near-matches of an amount in one ledger: rows in the same "
            "direction (money in or out) within pct_tolerance percent of the amount and "
            "within day_window days of the date. Use it for a one-sided item to check "
            "whether a counterpart exists under a different reference or none at all."),
        "parameters": {"type": "object", "properties": {
            "ledger": {"type": "string", "enum": ["bank", "gl"], "description": "The ledger to search IN."},
            "amount": {"type": "number", "description": "Signed INR amount to look for."},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "day_window": {"type": "integer", "description": "Days either side. Default 5."},
            "pct_tolerance": {"type": "number", "description": "Allowed difference in percent. Default 1."}},
            "required": ["ledger", "amount", "date"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "compare_amounts",
        "description": (
            "Does the arithmetic on two amounts so you never have to: difference, "
            "percentage difference, a as a percentage of b, which is smaller, whether "
            "the difference is divisible by 9, and whether both amounts use the same "
            "digits. Two swapped digits always give a difference divisible by 9 AND "
            "the same digits. Pass the bank amount as a and the GL amount as b."),
        "parameters": {"type": "object", "properties": {
            "amount_a": {"type": "number", "description": "Usually the bank amount."},
            "amount_b": {"type": "number", "description": "Usually the GL amount (the reference)."}},
            "required": ["amount_a", "amount_b"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "check_fx_explanation",
        "description": (
            "For a foreign-currency GL row: reports how much of the bank-vs-GL gap a change "
            "in exchange rate explains (foreign amount x (settlement-date market rate - GL "
            "rate)), and the bank's implied rate (bank INR / foreign amount) against the "
            "market rate. The implied rate is the key signal: within 0.5% of market means "
            "the full foreign amount settled, so the gap is FX. MORE than 0.5% away means "
            "the amount that settled was not the full foreign amount, so it is NOT an FX "
            "difference. gl_inr_consistent_with_its_rate=false means the GL rupee amount "
            "does not equal its own foreign amount x GL rate: a keying error, so check for "
            "transposition. Returns applicable=false for INR rows."),
        "parameters": {"type": "object", "properties": {
            "gl_id": {"type": "string", "description": "e.g. G01234"}},
            "required": ["gl_id"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "days_to_period_end",
        "description": (
            "For a date: days to its month end, whether it falls in the last 5 days of "
            "the month, and days to the bank statement end date. Useful when judging "
            "whether a GL-only item has simply not reached the bank yet."),
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["date"], "additionalProperties": False}}},
]

FUNCTIONS = {
    "get_exception": get_exception,
    "find_same_reference": find_same_reference,
    "search_other_ledger": search_other_ledger,
    "compare_amounts": compare_amounts,
    "check_fx_explanation": check_fx_explanation,
    "days_to_period_end": days_to_period_end,
}


def run_tool(name: str, arguments: dict) -> dict:
    """Run a tool the model asked for. Bad requests come back as an error, not a crash."""
    if name not in FUNCTIONS:
        return {"error": f"Unknown tool {name}."}
    try:
        return FUNCTIONS[name](**arguments)
    except Exception as exc:  # the model sent bad arguments
        return {"error": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    exception_id = sys.argv[1] if len(sys.argv) > 1 else "EXC-0001"
    print(json.dumps(get_exception(exception_id), indent=2))
