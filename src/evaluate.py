"""Phase 8 - Score the rules baseline and the agent against the answer key.

This is the ONLY file allowed to read data/answer_key.csv. Both methods are
scored on the same exceptions, the same way. "unclear" counts as wrong.

Run from the project folder:
    uv run python -m src.evaluate                  test set: the numbers you report
    uv run python -m src.evaluate --split dev      dev set, while tuning the prompt
    uv run python -m src.evaluate --errors 10      also list 10 wrong agent answers
    uv run python -m src.evaluate --log --readme   append to LOG.md, refresh README results

Writes results/report_<split>.md and results/metrics_<split>.json.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from src.common import BREAK_TYPES, DATA, LABELS, RESULTS, ROOT, SEED, load_split

SHORT = {"timing": "timing", "fx_difference": "fx", "partial_payment": "partial",
         "duplicate": "dup", "transposition": "transp", "missing_entry": "missing", "unclear": "unclear"}


def truth_table() -> pd.DataFrame:
    """Link every exception to the planted break whose rows it contains."""
    key = pd.read_csv(DATA / "answer_key.csv", dtype=str).fillna("")
    row_to_break = {}
    for r in key.itertuples():
        for row_id in [*r.bank_ids.split(";"), *r.gl_ids.split(";")]:
            if row_id:
                row_to_break[row_id] = (r.item_id, r.break_type, r.difficulty)
    exc = pd.read_csv(DATA / "exceptions.csv", dtype=str).fillna("")
    hits = [row_to_break.get(b) or row_to_break.get(g) for b, g in zip(exc["bank_id"], exc["gl_id"])]
    exc["item_id"] = [h[0] if h else None for h in hits]
    exc["true_type"] = [h[1] if h else None for h in hits]
    exc["difficulty"] = [h[2] if h else None for h in hits]
    exc.attrs["planted"] = len(key)
    exc.attrs["surfaced"] = exc["item_id"].nunique()
    return exc


def pct(x: float) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.1f}%"


def load_agent(split: str, run: int = 1) -> pd.DataFrame | None:
    suffix = ("" if split == "test" else f"_{split}") + ("" if run == 1 else f"_run{run}")
    path = DATA / f"predictions_agent{suffix}.csv"
    return pd.read_csv(path) if path.exists() else None


def load_traces(split: str) -> dict[str, dict]:
    path = DATA / ("traces.jsonl" if split == "test" else f"traces_{split}.jsonl")
    if not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {r["exception_id"]: r for r in records}


def evaluate(split: str) -> tuple[dict, pd.DataFrame]:
    truth = truth_table()
    ids = set(load_split().query("split == @split")["exception_id"])
    scope = truth[truth["exception_id"].isin(ids)].copy()
    not_planted = int(scope["true_type"].isna().sum())
    scope = scope[scope["true_type"].notna()]

    base = pd.read_csv(DATA / "predictions_baseline.csv")[["exception_id", "predicted_type"]]
    scope = scope.merge(base.rename(columns={"predicted_type": "rules"}), on="exception_id", how="left")
    agent = load_agent(split)
    has_agent = agent is not None and len(agent) > 0
    if has_agent:
        scope = scope.merge(agent.rename(columns={"predicted_type": "agent"}), on="exception_id", how="left")
        scope["agent"] = scope["agent"].fillna("not run")

    def acc(df, col):
        return float((df[col] == df["true_type"]).mean()) if len(df) else float("nan")

    matching = json.loads((DATA / "match_summary.json").read_text())
    generation = json.loads((DATA / "generation_summary.json").read_text())
    m = {
        "split": split,
        "evaluated_on": date.today().isoformat(),
        "seed": SEED,
        "n_transactions": generation["n_transactions"],
        "auto_match_rate_pct": matching["auto_match_rate_pct"],
        "exceptions_scored": len(scope),
        "exceptions_without_planted_break": not_planted,
        "planted_breaks_not_surfaced": generation["planted_breaks"] - truth.attrs["surfaced"],
        "hard_cases": int((scope["difficulty"] == "hard").sum()),
        "rules": {
            "accuracy": acc(scope, "rules"),
            "hard_accuracy": acc(scope[scope["difficulty"] == "hard"], "rules"),
            "unclear_rate": float((scope["rules"] == "unclear").mean()),
            "per_type": {t: acc(scope[scope["true_type"] == t], "rules") for t in BREAK_TYPES},
        },
        "agent": None,
    }
    m["per_type_n"] = {t: int((scope["true_type"] == t).sum()) for t in BREAK_TYPES}

    if has_agent:
        ran = scope[scope["agent"] != "not run"]
        traces = load_traces(split)
        m["agent"] = {
            "model": next(iter(traces.values()))["model"] if traces else None,
            "predictions": int(len(ran)),
            "accuracy": acc(scope, "agent"),
            "hard_accuracy": acc(scope[scope["difficulty"] == "hard"], "agent"),
            "unclear_rate": float((scope["agent"] == "unclear").mean()),
            "per_type": {t: acc(scope[scope["true_type"] == t], "agent") for t in BREAK_TYPES},
            "ungrounded_notes": int((~ran["grounded"].astype(bool)).sum()),
            "forced_unclear": int(sum(1 for r in traces.values() if r.get("forced_unclear"))),
            "label_repairs": int(sum(1 for r in traces.values() if r.get("label_repaired"))),
            "avg_tool_calls": float(ran["tool_calls"].mean()),
            "cost_usd": float(ran["cost_usd"].sum()),
            "cost_per_exception_usd": float(ran["cost_usd"].mean()),
            "accuracy_by_confidence": {
                c: {"n": int((ran["confidence"] == c).sum()), "accuracy": acc(ran[ran["confidence"] == c], "agent")}
                for c in ("high", "medium", "low")},
        }
        m["lift_pp"] = round(100 * (m["agent"]["accuracy"] - m["rules"]["accuracy"]), 1)

        run2 = load_agent(split, run=2)
        if run2 is not None:
            both = agent.merge(run2, on="exception_id", suffixes=("", "_2"))
            m["agent"]["stability"] = {"compared": int(len(both)),
                                      "labels_changed": int((both["predicted_type"] != both["predicted_type_2"]).sum())}
    return m, scope


def confusion_md(scope: pd.DataFrame, col: str) -> str:
    cm = confusion_matrix(scope["true_type"], scope[col], labels=LABELS)[: len(BREAK_TYPES)]
    header = "| true \\ predicted | " + " | ".join(SHORT[label] for label in LABELS) + " |"
    lines = [header, "|" + "---|" * (len(LABELS) + 1)]
    for t, row in zip(BREAK_TYPES, cm):
        lines.append(f"| {t} | " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def results_table(m: dict) -> str:
    a = m["agent"]
    name = f"test set, {m['exceptions_scored']} held-out exceptions" if m["split"] == "test" \
        else f"{m['split']} set, {m['exceptions_scored']} exceptions"
    lines = [
        f"Scored on the {name} · seed {m['seed']} · model {a['model'] if a else 'not run yet'} · {m['evaluated_on']}",
        "",
        "| Break type | n | Rules baseline | Agent |",
        "|---|---|---|---|",
    ]
    for t in BREAK_TYPES:
        lines.append(f"| {t} | {m['per_type_n'][t]} | {pct(m['rules']['per_type'][t])} | "
                     f"{pct(a['per_type'][t]) if a else 'not run yet'} |")
    lines += [
        f"| **Overall** | **{m['exceptions_scored']}** | **{pct(m['rules']['accuracy'])}** | "
        f"**{pct(a['accuracy']) if a else 'not run yet'}** |",
        f"| Hard cases only | {m['hard_cases']} | {pct(m['rules']['hard_accuracy'])} | "
        f"{pct(a['hard_accuracy']) if a else 'not run yet'} |",
        f"| Labelled unclear | | {pct(m['rules']['unclear_rate'])} | {pct(a['unclear_rate']) if a else 'not run yet'} |",
        "",
    ]
    if a:
        lines += [
            f"- **Lift:** {m['lift_pp']:+.1f} percentage points (agent minus rules)",
            f"- **Ungrounded notes:** {a['ungrounded_notes']} of {a['predictions']} "
            f"(a note citing a number no tool returned)",
            f"- **Cost:** ${a['cost_usd']:.2f} estimated, ${a['cost_per_exception_usd']:.4f} per exception, "
            f"{a['avg_tool_calls']:.1f} tool calls on average",
        ]
        if "stability" in a:
            s = a["stability"]
            lines.append(f"- **Stability:** {s['labels_changed']} of {s['compared']} labels changed on a second run")
    lines.append(f"- **Auto-match rate:** {m['auto_match_rate_pct']}% of all ledger rows cleared by SQL "
                 f"before any exception reached the agent ({m['n_transactions']:,} synthetic transactions)")
    return "\n".join(lines)


def report_md(m: dict, scope: pd.DataFrame) -> str:
    parts = [f"# Evaluation report: {m['split']} set", "", results_table(m), ""]
    a = m["agent"]
    if a:
        parts += ["## Agent accuracy by stated confidence", "", "| Confidence | n | Accuracy |", "|---|---|---|"]
        for c, v in a["accuracy_by_confidence"].items():
            parts.append(f"| {c} | {v['n']} | {pct(v['accuracy'])} |")
        parts += ["", "## Confusion matrix: agent (rows = true type)", "", confusion_md(scope, "agent"), ""]
    parts += ["## Confusion matrix: rules baseline (rows = true type)", "", confusion_md(scope, "rules"), ""]
    parts += [
        "## Coverage", "",
        f"- Exceptions scored: {m['exceptions_scored']}",
        f"- Exceptions with no planted break behind them (excluded): {m['exceptions_without_planted_break']}",
        f"- Planted breaks that never surfaced as an exception: {m['planted_breaks_not_surfaced']}",
    ]
    return "\n".join(parts) + "\n"


def write_errors(split: str, scope: pd.DataFrame, n: int) -> str:
    """Wrong agent answers with the tool steps behind them, for the error analysis."""
    wrong = scope[(scope["agent"] != scope["true_type"]) & (scope["agent"] != "not run")]
    wrong = wrong.sample(n=min(n, len(wrong)), random_state=SEED) if len(wrong) else wrong
    traces = load_traces(split)
    out = [f"# {len(wrong)} wrong agent answers ({split} set)", "",
           "For each: why did it go wrong? bad tool result / wrong reasoning / truly ambiguous.", ""]
    for r in wrong.sort_values("exception_id").itertuples():
        t = traces.get(r.exception_id, {})
        out += [f"## {r.exception_id}: true {r.true_type} ({r.difficulty}), agent said {r.agent}", "",
                f"Confidence: {t.get('confidence')} · forced unclear: {t.get('forced_unclear')}", "",
                f"Note: {t.get('note')}", "", "Tool calls:"]
        for s in t.get("steps", []):
            if "tool" in s:
                out.append(f"- `{s['tool']}({json.dumps(s['arguments'])})` -> `{json.dumps(s['result'])[:400]}`")
        out.append("")
    text = "\n".join(out)
    (RESULTS / f"errors_{split}.md").write_text(text, encoding="utf-8")
    return text


def append_log(m: dict) -> None:
    a = m["agent"]
    lines = [f"\n## {m['evaluated_on']} · evaluation, {m['split']} set", "",
             f"- Seed {m['seed']}; model {a['model'] if a else 'agent not run'}",
             f"- Exceptions scored (M): {m['exceptions_scored']}, of which hard: {m['hard_cases']}",
             f"- Rules baseline accuracy (Z): {pct(m['rules']['accuracy'])}; hard cases {pct(m['rules']['hard_accuracy'])}"]
    if a:
        lines += [f"- Agent accuracy (Y): {pct(a['accuracy'])}; hard cases {pct(a['hard_accuracy'])}",
                  f"- Lift: {m['lift_pp']:+.1f} pp",
                  f"- Agent unclear rate: {pct(a['unclear_rate'])}; ungrounded notes: {a['ungrounded_notes']}; "
                  f"forced unclear: {a['forced_unclear']}; labels repaired: {a['label_repairs']}",
                  f"- Estimated cost: ${a['cost_usd']:.2f} (${a['cost_per_exception_usd']:.4f} per exception)"]
        if "stability" in a:
            lines.append(f"- Stability: {a['stability']['labels_changed']} of {a['stability']['compared']} labels changed")
        lines.append("- Per type (rules / agent): " + "; ".join(
            f"{t} {pct(m['rules']['per_type'][t])} / {pct(a['per_type'][t])}" for t in BREAK_TYPES))
    path = ROOT / "LOG.md"
    text = path.read_text(encoding="utf-8")
    block = "\n".join(lines) + "\n"
    marker = "\n## Error analysis"
    # Keep results in the "Agent runs" part of the log, above the error analysis.
    text = text.replace(marker, block + marker, 1) if marker in text else text + block
    path.write_text(text, encoding="utf-8")


def update_readme(m: dict) -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    block = f"<!-- RESULTS:START -->\n{results_table(m)}\n<!-- RESULTS:END -->"
    text = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->", lambda _: block, text, flags=re.DOTALL)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score rules baseline and agent against the answer key.")
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    parser.add_argument("--errors", type=int, default=0, help="list N wrong agent answers")
    parser.add_argument("--log", action="store_true", help="append the results to LOG.md")
    parser.add_argument("--readme", action="store_true", help="refresh the results table in README.md")
    args = parser.parse_args()

    m, scope = evaluate(args.split)
    RESULTS.mkdir(exist_ok=True)
    report = report_md(m, scope)
    (RESULTS / f"report_{args.split}.md").write_text(report, encoding="utf-8")
    (RESULTS / f"metrics_{args.split}.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(report)
    if args.errors and m["agent"]:
        print(write_errors(args.split, scope, args.errors))
    if args.log:
        append_log(m)
        print("Appended to LOG.md")
    if args.readme:
        if args.split != "test":
            print("README not updated: only test-set numbers belong in the README.")
        else:
            update_readme(m)
            print("README.md results table refreshed")


if __name__ == "__main__":
    main()
