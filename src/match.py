"""Phase 4 - Run the SQL matching, check it, and save matches and exceptions.

Run from the project folder:
    uv run python -m src.match

Reads data/bank.csv and data/gl.csv, runs sql/match.sql in DuckDB (an
in-process database: no server, it queries the CSV files directly) and writes:
    data/matched.csv        bank_id, gl_id, pass
    data/exceptions.csv     exception_id, kind, bank_id, gl_id
    data/split.csv          which exceptions are dev (prompt tuning) vs test
    data/match_summary.json the numbers for LOG.md
Stops loudly if any row is lost or double-counted.
"""
from __future__ import annotations

import json
import os
import sys

import duckdb
import pandas as pd

from src.common import DATA, ROOT, SQL, make_split, write_csv


def run_matching() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    os.chdir(ROOT)  # match.sql uses paths relative to the project folder
    con = duckdb.connect()
    con.execute((SQL / "match.sql").read_text())

    matched = con.sql("SELECT bank_id, gl_id, pass FROM matched ORDER BY bank_id").df()
    exceptions = con.sql("SELECT exception_id, kind, bank_id, gl_id FROM exceptions ORDER BY exception_id").df()
    n_bank = con.sql("SELECT count(*) FROM bank").fetchone()[0]
    n_gl = con.sql("SELECT count(*) FROM gl").fetchone()[0]

    # ---- check 1: every row lands exactly once, in matched or in exceptions
    problems = []
    for col, total, name in [("bank_id", n_bank, "bank"), ("gl_id", n_gl, "GL")]:
        seen = pd.concat([matched[col], exceptions[col].dropna()])
        if seen.duplicated().any():
            problems.append(f"{name} rows used twice: {sorted(seen[seen.duplicated()])[:5]}")
        if seen.nunique() != total:
            problems.append(f"{name} rows: {total} in the file but {seen.nunique()} accounted for")

    # ---- check 2: every matched pair has identical amounts
    unequal = con.sql("""
        SELECT count(*) FROM matched m
        JOIN bank b USING (bank_id) JOIN gl g USING (gl_id)
        WHERE b.amount_inr <> g.amount_inr
    """).fetchone()[0]
    if unequal:
        problems.append(f"{unequal} matched pairs have different amounts")

    if problems:
        print("MATCHING CHECKS FAILED:")
        for p in problems:
            print("  -", p)
        sys.exit(1)

    pairs = len(matched)
    total_rows = int(n_bank + n_gl)
    summary = {
        "bank_rows": int(n_bank),
        "gl_rows": int(n_gl),
        "total_rows": total_rows,
        "matched_pairs": pairs,
        "matched_pass1": int((matched["pass"] == 1).sum()),
        "matched_pass2": int((matched["pass"] == 2).sum()),
        "rows_cleared": 2 * pairs,
        "auto_match_rate_pct": round(100 * 2 * pairs / total_rows, 2),
        "bank_rows_matched_pct": round(100 * pairs / n_bank, 2),
        "exceptions": len(exceptions),
        "exceptions_by_kind": {k: int(v) for k, v in exceptions["kind"].value_counts().sort_index().items()},
    }
    return matched, exceptions, summary


def main() -> None:
    matched, exceptions, summary = run_matching()
    write_csv(matched, DATA / "matched.csv")
    write_csv(exceptions, DATA / "exceptions.csv")
    split = make_split(exceptions["exception_id"].tolist())
    summary["dev_exceptions"] = int((split["split"] == "dev").sum())
    summary["test_exceptions"] = int((split["split"] == "test").sum())
    (DATA / "match_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    s = summary
    print("Both checks passed: every row accounted for once, matched amounts identical.\n")
    print(f"Rows: {s['bank_rows']:,} bank + {s['gl_rows']:,} GL = {s['total_rows']:,}")
    print(f"Matched pairs: {s['matched_pairs']:,} (pass 1: {s['matched_pass1']:,}, pass 2: {s['matched_pass2']:,})")
    print(f"Auto-match rate: {s['auto_match_rate_pct']}% of all rows cleared by SQL "
          f"({s['bank_rows_matched_pct']}% of bank rows)")
    print(f"Exceptions: {s['exceptions']} -> " + ", ".join(f"{k} {v}" for k, v in s["exceptions_by_kind"].items()))
    print(f"Split: {s['dev_exceptions']} dev, {s['test_exceptions']} test")


if __name__ == "__main__":
    main()
