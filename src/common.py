"""Shared settings and small helpers used by every script.

Keeping these in one place means the break labels, file paths and the
dev/test split can never drift apart between files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SQL = ROOT / "sql"

SEED = 42
PERIOD_END = "2026-09-30"  # the bank statement / quarter end date
DEV_SIZE = 50  # exceptions set aside for prompt tuning

BREAK_TYPES = [
    "timing",
    "fx_difference",
    "partial_payment",
    "duplicate",
    "transposition",
    "missing_entry",
]
LABELS = BREAK_TYPES + ["unclear"]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a CSV the same way on every operating system (so re-runs are identical)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, lineterminator="\n")


# ---------------------------------------------------------------- arithmetic
# All amount checks work in whole paise (integers), never in floats, so that
# "divisible by 9" and "same digits" are exact.

def to_paise(amount: float) -> int:
    return int(round(abs(float(amount)) * 100))


def divisible_by_9(a: float, b: float) -> bool:
    diff = abs(to_paise(a) - to_paise(b))
    return diff != 0 and diff % 9 == 0


def same_digits(a: float, b: float) -> bool:
    return sorted(str(to_paise(a))) == sorted(str(to_paise(b)))


# ---------------------------------------------------------------- dev / test split

def make_split(exception_ids: list[str]) -> pd.DataFrame:
    """Randomly set aside DEV_SIZE exceptions for prompt tuning; the rest are the test set."""
    rng = np.random.default_rng(SEED)
    ids = np.array(sorted(exception_ids))
    dev = set(rng.choice(ids, size=min(DEV_SIZE, len(ids)), replace=False))
    split = pd.DataFrame({"exception_id": ids, "split": ["dev" if i in dev else "test" for i in ids]})
    write_csv(split, DATA / "split.csv")
    return split


def load_split() -> pd.DataFrame:
    return pd.read_csv(DATA / "split.csv")
