"""Phase 3 - Generate synthetic bank and GL ledgers with planted breaks.

Run from the project folder:
    uv run python -m src.generate_data

Writes four files to data/:
    bank.csv        the bank statement for the quarter
    gl.csv          the company's general-ledger (GL) cash account
    fx_rates.csv    one USD/INR market rate per day
    answer_key.csv  which break was planted on which rows
                    (ONLY src/evaluate.py is allowed to read this file)

Everything comes from one random seed, so every run produces identical files.
Amounts are signed from the company's point of view: + money in, - money out.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.common import BREAK_TYPES, DATA, PERIOD_END, SEED, write_csv

N_TRANSACTIONS = 5_000
QUARTER_START = pd.Timestamp("2026-07-01")
QUARTER_END = pd.Timestamp(PERIOD_END)
USD_SHARE = 0.15            # share of transactions in US dollars
RECEIPT_SHARE = 0.45        # share that are money in (the rest are payments)
MISSING_REF_SHARE = 0.20    # bank rows that arrive without a reference number
FX_SHOCK_DATE = pd.Timestamp("2026-08-14")  # one-day rupee depreciation

# How many of each break to plant, and how many of those are deliberately hard.
BREAKS = {
    "timing":          {"total": 68, "hard": 22},  # hard: mid-month, not month-end
    "fx_difference":   {"total": 68, "hard": 20},  # hard: big rate swing (> 2%)
    "partial_payment": {"total": 66, "hard": 28},  # hard: 95-99% paid, looks like FX
    "duplicate":       {"total": 64, "hard": 20},  # hard: re-keyed with a different reference
    "transposition":   {"total": 66, "hard": 0},
    "missing_entry":   {"total": 68, "hard": 28},  # hard: vague bank description
}

INR_NAME_A = ["Sharma", "Gupta", "Patel", "Reliable", "Sunrise", "Apex", "Shree Ganesh",
              "Krishna", "Bharat", "Om Sai", "Metro", "Vardhman", "Nirmal", "Pioneer",
              "Zenith", "Coastal", "Deccan", "Himalaya", "Kaveri", "Lotus", "Sagar",
              "Trimurti", "Mahalaxmi", "Balaji", "Ganga", "Royal", "Classic", "Galaxy",
              "Unity", "Venkatesh"]
INR_NAME_B = ["Traders", "Logistics", "Enterprises", "Industries", "Textiles", "Steel",
              "Pharma", "Packaging", "Agencies", "Motors", "Foods", "Chemicals",
              "Electricals", "Polymers", "Castings", "Distributors", "Engineering"]
INR_SUFFIX = ["Pvt Ltd", "Pvt Ltd", "Pvt Ltd", "LLP", "Ltd", "& Co"]
USD_NAMES = ["Acme Corp", "Northwind Trading LLC", "Blue Harbor Inc", "Kestrel Systems Inc",
             "Harborline Foods LLC", "Silverleaf GmbH", "Maple Ridge Supply Co",
             "Orion Components Ltd", "Brightwater Retail Inc", "Cobalt Freight LLC",
             "Summit Apparel Inc", "Redwood Analytics Inc", "Granite Tools Co",
             "Pacific Rim Traders", "Evergreen Medical Inc", "Atlas Marine LLC",
             "Beacon Labs Inc", "Crescent Imports Ltd", "Falcon Aero Parts Inc",
             "Lakeside Paper Co"]

# Bank-only items the GL never recorded. Clear ones carry the usual bank codes.
CLEAR_MISSING = [
    ("ACCT MAINT CHG", -590.00), ("SMS ALERT CHARGES", -17.70), ("CHQ BOOK CHG", -118.00),
    ("NEFT CHG", None), ("RTGS CHG", -59.00), ("IMPS FEE", -11.80),
    ("DEBIT CARD ANNUAL FEE", -885.00), ("CASH HANDLING CHARGES", -354.00),
    ("STOP PMT CHG", -236.00), ("FOREX CHG SWIFT", -1180.00),
    ("INT CR SWEEP FD", None), ("INT PD SB ACCT", None),
]
# Vague ones: nothing in the text says "charge" or "interest".
VAGUE_MISSING = ["NACH DR {code} HDFCERGO", "ACH DR {code}", "SI DR {code}", "BY TRF {code}",
                 "TRF TO {code}", "MISC DR {code}", "ADJ ENTRY {code}", "CLG RTN {code}",
                 "UPI/{code}/PAYTM", "NEFT CR {cp}", "IMPS DR {cp}"]
VAGUE_CREDITS = {"BY TRF {code}", "NEFT CR {cp}"}


def day(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%d")


def make_fx_rates(rng: np.random.Generator) -> pd.Series:
    """A slowly drifting USD/INR rate with one sharp depreciation day."""
    dates = pd.date_range("2026-04-01", "2026-10-10", freq="D")
    log_returns = rng.normal(0.00005, 0.0018, len(dates))
    log_returns[dates.get_loc(FX_SHOCK_DATE)] += 0.028
    rates = 86.40 * np.exp(np.cumsum(log_returns))
    return pd.Series(np.round(rates, 4), index=dates)


def make_counterparties(rng: np.random.Generator, n: int = 140) -> list[str]:
    names: set[str] = set()
    while len(names) < n:
        names.add(f"{rng.choice(INR_NAME_A)} {rng.choice(INR_NAME_B)} {rng.choice(INR_SUFFIX)}")
    return sorted(names)


def swap_spots(amount: float) -> list[int]:
    """Positions where two neighbouring rupee digits differ (swapping them changes the amount)."""
    s = str(int(round(abs(amount) * 100)) // 100)
    return [i for i in range(len(s) - 1) if s[i] != s[i + 1] and not (i == 0 and s[1] == "0")]


def transpose_digits(amount: float, rng: np.random.Generator) -> float:
    """Swap two neighbouring rupee digits, the classic keying error (e.g. 45,120 -> 45,210)."""
    paise = int(round(abs(amount) * 100))
    rupees, cents = divmod(paise, 100)
    s = str(rupees)
    i = int(rng.choice(swap_spots(amount)))
    swapped = s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return float(np.sign(amount)) * (int(swapped) * 100 + cents) / 100


def rekey_reference(reference: str, rng: np.random.Generator) -> str:
    """How a second, careless keying mangles a reference: two digits swapped or the prefix dropped."""
    prefix, number = reference.split("-")
    spots = [i for i in range(len(number) - 1) if number[i] != number[i + 1]]
    if spots and rng.random() < 0.6:
        i = int(rng.choice(spots))
        return f"{prefix}-{number[:i]}{number[i + 1]}{number[i]}{number[i + 2:]}"
    return number


def make_transactions(rng, rates, customers) -> list[dict]:
    """5,000 genuine transactions, each due to appear in both ledgers."""
    n_days = (QUARTER_END - QUARTER_START).days + 1
    ref_numbers = rng.choice(np.arange(100_000, 1_000_000), size=N_TRANSACTIONS, replace=False)
    txns = []
    for i in range(N_TRANSACTIONS):
        receipt = bool(rng.random() < RECEIPT_SHARE)
        sign = 1.0 if receipt else -1.0
        gl_date = QUARTER_START + pd.Timedelta(days=int(rng.integers(0, n_days)))
        t = {"key": f"T{i:04d}", "receipt": receipt, "gl_date": gl_date,
             "bank_ref": bool(rng.random() >= MISSING_REF_SHARE), "has_bank": True,
             "break_type": None, "difficulty": None, "chq_no": int(rng.integers(1, 999_999))}

        if rng.random() < USD_SHARE:
            t["currency"] = "USD"
            t["counterparty"] = str(rng.choice(USD_NAMES))
            t["channel"] = "SWIFT"
            t["amount_fx"] = round(float(np.clip(rng.lognormal(np.log(2500), 1.0), 150, 150_000)), 2)
            t["reference"] = f"{'EXP' if receipt else 'IMP'}-{ref_numbers[i]}"
            t["bank_date"] = min(gl_date + pd.Timedelta(days=int(rng.integers(0, 2))), QUARTER_END)
            # The bank converts at the day's market rate less (receipts) or plus (payments) its spread.
            spread = rng.uniform(0.05, 0.25)
            bank_rate = rates[t["bank_date"]] - spread if receipt else rates[t["bank_date"]] + spread
            t["bank_amount"] = sign * round(t["amount_fx"] * bank_rate, 2)
            # Correct booking: the GL records the rupees actually credited or debited.
            t["gl_amount"] = t["bank_amount"]
            t["fx_rate"] = round(abs(t["gl_amount"]) / t["amount_fx"], 4)
        else:
            t["currency"] = "INR"
            t["counterparty"] = str(rng.choice(customers))
            amount = float(np.clip(rng.lognormal(np.log(60_000), 1.3), 500, 5_000_000))
            amount = float(round(amount)) if rng.random() < 0.25 else round(amount, 2)
            if amount > 200_000 and rng.random() < 0.6:
                t["channel"] = "RTGS"
            else:
                t["channel"] = str(rng.choice(["NEFT", "IMPS", "CHQ"], p=[0.55, 0.20, 0.25]))
            lag = int(rng.integers(1, 4)) if t["channel"] == "CHQ" else int(rng.choice([0, 1, 2, 3], p=[0.35, 0.35, 0.2, 0.1]))
            prefix = "INV" if receipt else str(rng.choice(["PO", "BILL"]))
            t["reference"] = f"{prefix}-{ref_numbers[i]}"
            t["bank_date"] = min(gl_date + pd.Timedelta(days=lag), QUARTER_END)
            t["amount_fx"] = None
            t["fx_rate"] = None
            t["bank_amount"] = t["gl_amount"] = sign * amount
        txns.append(t)
    return txns


def plant_breaks(rng, txns, rates) -> list[dict]:
    """Modify chosen transactions so each carries exactly one break. Returns duplicate GL rows."""
    used: set[int] = set()

    def pick(n: int, condition) -> list[int]:
        pool = [i for i, t in enumerate(txns) if i not in used and condition(t)]
        chosen = [int(x) for x in rng.choice(pool, size=n, replace=False)]
        used.update(chosen)
        return chosen

    def mark(i, kind, hard):
        txns[i]["break_type"] = kind
        txns[i]["difficulty"] = "hard" if hard else "regular"

    # FX difference: the GL converted at the old invoice-date rate; the bank settled at today's rate.
    spec = BREAKS["fx_difference"]
    hard = pick(spec["hard"], lambda t: t["currency"] == "USD" and t["gl_date"] >= pd.Timestamp("2026-08-20"))
    regular = pick(spec["total"] - spec["hard"], lambda t: t["currency"] == "USD" and (
        t["gl_date"] < FX_SHOCK_DATE or t["gl_date"] >= pd.Timestamp("2026-09-13")))
    for i in hard + regular:
        t = txns[i]
        if i in hard:  # invoiced before the shock, settled after it
            earliest = t["gl_date"] - pd.Timedelta(days=75)
            span = (pd.Timestamp("2026-08-09") - earliest).days
            invoice_date = earliest + pd.Timedelta(days=int(rng.integers(0, span + 1)))
        else:
            invoice_date = t["gl_date"] - pd.Timedelta(days=int(rng.integers(7, 31)))
        t["fx_rate"] = float(rates[invoice_date])
        t["gl_amount"] = (1.0 if t["receipt"] else -1.0) * round(t["amount_fx"] * t["fx_rate"], 2)
        t["bank_ref"] = True
        mark(i, "fx_difference", i in hard)

    # Partial payment: the customer paid only part; the GL recorded the full invoice.
    spec = BREAKS["partial_payment"]
    n_hard_usd = round(spec["hard"] * 0.6)
    n_reg = spec["total"] - spec["hard"]
    n_reg_usd = round(n_reg * 0.2)
    groups = [
        (pick(n_hard_usd, lambda t: t["receipt"] and t["currency"] == "USD"), True),
        (pick(spec["hard"] - n_hard_usd, lambda t: t["receipt"] and t["currency"] == "INR"), True),
        (pick(n_reg_usd, lambda t: t["receipt"] and t["currency"] == "USD"), False),
        (pick(n_reg - n_reg_usd, lambda t: t["receipt"] and t["currency"] == "INR"), False),
    ]
    for chosen, is_hard in groups:
        for i in chosen:
            t = txns[i]
            share = rng.uniform(0.95, 0.99) if is_hard else rng.uniform(0.30, 0.90)
            paid = t["gl_amount"] * share
            if t["currency"] == "INR" and not is_hard and rng.random() < 0.5:
                paid = float(round(paid))  # customers often pay a round figure
            t["bank_amount"] = round(paid, 2)
            t["bank_ref"] = True
            mark(i, "partial_payment", is_hard)

    # Timing: recorded in the GL, not yet through the bank by the statement date.
    spec = BREAKS["timing"]
    for i in pick(spec["hard"], lambda t: not t["receipt"]):  # outstanding cheques from mid-month
        txns[i]["gl_date"] = pd.Timestamp("2026-09-03") + pd.Timedelta(days=int(rng.integers(0, 20)))
        txns[i]["has_bank"] = False
        mark(i, "timing", True)
    for i in pick(spec["total"] - spec["hard"], lambda t: True):  # month-end items
        txns[i]["gl_date"] = pd.Timestamp("2026-09-26") + pd.Timedelta(days=int(rng.integers(0, 5)))
        txns[i]["has_bank"] = False
        mark(i, "timing", False)

    # Duplicate: the same GL entry keyed a second time, a few days later at most.
    # Hard ones were re-keyed with a slightly different reference, so a simple
    # same-reference check cannot see the twin.
    duplicates = []
    spec = BREAKS["duplicate"]
    for n, i in enumerate(pick(spec["total"], lambda t: True)):
        t = txns[i]
        is_hard = n < spec["hard"]
        again = dict(t)
        again["key"] = t["key"] + "-DUP"
        if is_hard:
            again["reference"] = rekey_reference(t["reference"], rng)
            lag = int(rng.integers(1, 6))
        else:
            lag = int(rng.choice([0, 1, 2, 3], p=[0.3, 0.3, 0.25, 0.15]))
        again["gl_date"] = min(t["gl_date"] + pd.Timedelta(days=lag), QUARTER_END)
        duplicates.append(again)
        mark(i, "duplicate", is_hard)

    # Transposition: two neighbouring digits swapped when the GL entry was keyed.
    for i in pick(BREAKS["transposition"]["total"], lambda t: len(swap_spots(t["gl_amount"])) > 0):
        t = txns[i]
        t["gl_amount"] = transpose_digits(t["gl_amount"], rng)
        t["bank_ref"] = True
        mark(i, "transposition", False)

    return duplicates


def make_missing_entries(rng, customers) -> list[dict]:
    """Bank-only rows: charges, interest and debits the GL never recorded."""
    spec = BREAKS["missing_entry"]
    n_days = (QUARTER_END - QUARTER_START).days + 1
    month_ends = [pd.Timestamp("2026-07-31"), pd.Timestamp("2026-08-31"), QUARTER_END]
    extra_refs = rng.choice(np.arange(100_000, 1_000_000), size=spec["total"], replace=False)
    rows = []
    for k in range(spec["total"]):
        is_hard = k >= spec["total"] - spec["hard"]
        row = {"key": f"M{k:03d}", "reference": None, "break_type": "missing_entry",
               "difficulty": "hard" if is_hard else "regular"}
        if not is_hard:
            text, amount = CLEAR_MISSING[int(rng.integers(0, len(CLEAR_MISSING)))]
            date = month_ends[int(rng.integers(0, 3))] if rng.random() < 0.5 else \
                QUARTER_START + pd.Timedelta(days=int(rng.integers(0, n_days)))
            if amount is None:
                amount = round(float(rng.lognormal(np.log(8_000), 0.8)), 2) if text.startswith("INT") \
                    else -round(float(rng.choice([2.5, 5, 15, 25])) * 1.18, 2)
            row["description"] = f"{text} {date.strftime('%b%y').upper()}"
        else:
            template = VAGUE_MISSING[int(rng.integers(0, len(VAGUE_MISSING)))]
            date = QUARTER_START + pd.Timedelta(days=int(rng.integers(0, n_days)))
            code = str(int(rng.integers(100_000, 9_999_999)))
            cp = str(rng.choice(customers)).upper()
            row["description"] = template.format(code=code, cp=cp)
            if template in VAGUE_CREDITS:
                amount = round(float(rng.lognormal(np.log(60_000), 1.2)), 2)
                if template == "NEFT CR {cp}" and rng.random() < 0.5:
                    row["reference"] = f"INV-{extra_refs[k]}"  # an invoice number the GL never saw
            else:
                amount = -round(float(rng.lognormal(np.log(15_000), 1.0)), 2)
        row["bank_date"] = date
        row["bank_amount"] = amount
        row["description"] = row["description"][:24].rstrip()
        rows.append(row)
    return rows


def bank_description(t: dict) -> str:
    """Banks upper-case and truncate whatever the payer sent."""
    if t["channel"] == "CHQ":
        text = f"CHQ {'DEP' if t['receipt'] else 'PAID'} {t['chq_no']:06d}"
    elif t["channel"] == "SWIFT":
        text = f"SWIFT {'INW' if t['receipt'] else 'OUT'} {t['counterparty'].upper()}"
    else:
        text = f"{t['channel']} {'CR' if t['receipt'] else 'DR'} {t['counterparty'].upper()}"
    return text[:24].rstrip()


def assign_ids(df: pd.DataFrame, date_col: str, id_col: str, prefix: str, rng) -> pd.DataFrame:
    """Number rows in date order with a random tie-break, so IDs reveal nothing about breaks."""
    df = df.assign(_tie=rng.random(len(df))).sort_values([date_col, "_tie"]).drop(columns="_tie")
    df.insert(0, id_col, [f"{prefix}{n:05d}" for n in range(1, len(df) + 1)])
    return df.reset_index(drop=True)


def main() -> None:
    rng = np.random.default_rng(SEED)
    rates = make_fx_rates(rng)
    customers = make_counterparties(rng)
    txns = make_transactions(rng, rates, customers)
    duplicates = plant_breaks(rng, txns, rates)
    missing = make_missing_entries(rng, customers)

    # ---- bank statement
    bank_rows = [{"key": t["key"], "value_date": t["bank_date"], "amount_inr": t["bank_amount"],
                  "description": bank_description(t),
                  "reference": t["reference"] if t["bank_ref"] else None}
                 for t in txns if t["has_bank"]]
    bank_rows += [{"key": m["key"], "value_date": m["bank_date"], "amount_inr": m["bank_amount"],
                   "description": m["description"], "reference": m["reference"]} for m in missing]
    bank = assign_ids(pd.DataFrame(bank_rows), "value_date", "bank_id", "B", rng)

    # ---- general ledger
    gl_rows = [{"key": t["key"], "posting_date": t["gl_date"], "amount_inr": t["gl_amount"],
                "currency": t["currency"], "amount_fx": t["amount_fx"], "fx_rate": t["fx_rate"],
                "counterparty": t["counterparty"], "reference": t["reference"]}
               for t in txns + duplicates]
    gl = assign_ids(pd.DataFrame(gl_rows), "posting_date", "gl_id", "G", rng)

    # ---- answer key (row IDs per planted break)
    bank_id = dict(zip(bank["key"], bank["bank_id"]))
    gl_id = dict(zip(gl["key"], gl["gl_id"]))
    key_rows = []
    for t in txns:
        if t["break_type"] is None:
            continue
        bank_ids = [bank_id[t["key"]]] if t["has_bank"] and t["break_type"] != "duplicate" else []
        gl_ids = [gl_id[t["key"]]] + ([gl_id[t["key"] + "-DUP"]] if t["break_type"] == "duplicate" else [])
        key_rows.append({"break_type": t["break_type"], "difficulty": t["difficulty"],
                         "bank_ids": ";".join(bank_ids), "gl_ids": ";".join(gl_ids)})
    for m in missing:
        key_rows.append({"break_type": "missing_entry", "difficulty": m["difficulty"],
                         "bank_ids": bank_id[m["key"]], "gl_ids": ""})
    key = pd.DataFrame(key_rows)
    key = key.assign(_tie=rng.random(len(key))).sort_values("_tie").drop(columns="_tie")
    key.insert(0, "item_id", [f"BRK-{n:04d}" for n in range(1, len(key) + 1)])

    # ---- tidy formats and save
    bank["value_date"] = bank["value_date"].map(day)
    bank["amount_inr"] = bank["amount_inr"].map(lambda x: f"{x:.2f}")
    gl["posting_date"] = gl["posting_date"].map(day)
    gl["amount_inr"] = gl["amount_inr"].map(lambda x: f"{x:.2f}")
    gl["amount_fx"] = gl["amount_fx"].map(lambda x: "" if pd.isna(x) else f"{x:.2f}")
    gl["fx_rate"] = gl["fx_rate"].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
    fx = pd.DataFrame({"date": [day(d) for d in rates.index], "usd_inr": [f"{r:.4f}" for r in rates]})

    DATA.mkdir(exist_ok=True)
    write_csv(bank.drop(columns="key"), DATA / "bank.csv")
    write_csv(gl.drop(columns="key"), DATA / "gl.csv")
    write_csv(fx, DATA / "fx_rates.csv")
    write_csv(key, DATA / "answer_key.csv")

    counts = key["break_type"].value_counts().reindex(BREAK_TYPES)
    hard = key[key["difficulty"] == "hard"]["break_type"].value_counts().reindex(BREAK_TYPES).fillna(0).astype(int)
    summary = {
        "seed": SEED, "n_transactions": N_TRANSACTIONS, "usd_share": USD_SHARE,
        "bank_rows": len(bank), "gl_rows": len(gl), "planted_breaks": len(key),
        "breaks_by_type": {b: int(counts[b]) for b in BREAK_TYPES},
        "hard_by_type": {b: int(hard[b]) for b in BREAK_TYPES},
    }
    (DATA / "generation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Seed {SEED}: {N_TRANSACTIONS:,} genuine transactions, {len(key)} planted breaks")
    print(f"bank.csv {len(bank):,} rows | gl.csv {len(gl):,} rows | fx_rates.csv {len(fx)} days")
    print("\nBreaks planted (of which hard):")
    for b in BREAK_TYPES:
        print(f"  {b:<16} {counts[b]:>4}  ({hard[b]} hard)")


if __name__ == "__main__":
    main()
