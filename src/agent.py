"""Phase 7 - The agent loop: one exception in, a label and an investigation note out.

Uses the OpenAI API's own tool calling directly (no LangChain), so every step
is plain code. The model asks for tools, this file runs them, and the loop ends
when the model answers in JSON. After 6 tool calls the answer is forced to
"unclear", so a confused agent cannot loop forever or run up cost.

Run from the project folder (needs OPENAI_API_KEY in .env):
    uv run python -m src.agent --one EXC-0027      one exception, every step printed
    uv run python -m src.agent --split dev         the 50 dev items (tune the prompt on these)
    uv run python -m src.agent --split test        the test set: run ONCE, at the end
    uv run python -m src.agent --split dev --run 2 dev again, to check stability

Outputs (dev -> *_dev files, test -> the plain names):
    data/predictions_agent.csv   exception_id, predicted_type, confidence, grounded
    data/traces.jsonl            every tool call, result and answer, one line per exception
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from dotenv import load_dotenv

from src.common import DATA, LABELS, load_split, write_csv
from src.tools import TOOLS, run_tool

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_TOOL_CALLS = 6
# USD per million tokens, used only to estimate spend. Check the pricing page for
# your model and override in .env if different. Your OpenAI usage page is the truth.
PRICE_INPUT = float(os.getenv("OPENAI_PRICE_INPUT_PER_M", "0.40"))
PRICE_CACHED = float(os.getenv("OPENAI_PRICE_CACHED_INPUT_PER_M", "0.10"))
PRICE_OUTPUT = float(os.getenv("OPENAI_PRICE_OUTPUT_PER_M", "1.60"))

SYSTEM_PROMPT = """You are a bank reconciliation analyst. You triage ONE open exception between a
company's bank statement and its general-ledger (GL) cash account.

Classify it as exactly one of:
- timing: in the GL but not yet through the bank by the statement date (outstanding cheque or deposit in transit). No second GL entry with the same reference.
- fx_difference: foreign-currency item; the GL converted at a different exchange rate from the bank's settlement rate, but the full foreign amount settled.
- partial_payment: only part of the recorded amount was paid; the bank amount is smaller than the GL amount and an exchange-rate change does not explain the gap.
- duplicate: the same GL entry was posted twice (two GL rows with the same reference and amount, only one bank row).
- transposition: two digits swapped when keying an amount; the difference is divisible by 9 AND both amounts use the same digits.
- missing_entry: the bank did something the GL never recorded (bank charges, interest, direct debits, unrecorded receipts or payments). Bank-only.
- unclear: the evidence does not clearly support one type.

How to investigate:
- Always start with get_exception.
- amount_mismatch: call compare_amounts with the bank amount as a and the GL amount as b. If the difference is divisible by 9 AND the amounts use the same digits, it is a transposition, even for a foreign-currency row. Otherwise, for a foreign-currency GL row, call check_fx_explanation: it is an fx_difference only if the bank implied rate is within 0.5% of the market rate; further away than that, the full foreign amount did not settle.
- gl_only: call find_same_reference to see whether the entry was posted twice. If two GL rows share the reference and amount but there is only one bank row, the open one is a duplicate, even when it is the earlier of the two: it does not matter which copy the bank was matched to. A careless second keying can carry a slightly different reference, so if no twin shares the reference, also search the gl ledger itself (search_other_ledger with ledger "gl", pct_tolerance 0) for an entry with the same amount and counterparty a few days apart. days_to_period_end helps judge timing.
- bank_only: call search_other_ledger on the gl ledger to confirm no GL counterpart exists.

Rules:
1. Never calculate anything yourself. Every number, difference, percentage and date gap must come from a tool.
2. Every fact and number in your note must appear in a tool result for this exception.
3. You may make at most 6 tool calls. Most exceptions need 2 to 4.
4. Confidence: "high" only when every check points the same way; "medium" when a signal is borderline or conflicts; "low" when you are unsure.
5. break_type must be one of the seven labels above, never an exception kind such as amount_mismatch, bank_only or gl_only.
6. When you have enough evidence, reply with ONLY a JSON object, no other text:
{"break_type": "<one label above>", "confidence": "high" | "medium" | "low",
 "evidence": ["short fact taken from a tool result", "..."],
 "note": "2-3 sentence investigation note for the reviewing accountant"}"""

# Thresholds that appear in the instructions, which a note may legitimately quote.
INSTRUCTION_NUMBERS = {0.5, 2, 3, 4, 5, 6, 9}
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


# ---------------------------------------------------------------- OpenAI plumbing

def get_client():
    """Create the OpenAI client, with a clear message if the key is missing."""
    from openai import OpenAI

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set. Put a line OPENAI_API_KEY=sk-... in the .env file "
                 "in the project folder (no quotes, no spaces).")
    return OpenAI(max_retries=5, timeout=90)


_unsupported: set[str] = set()  # settings a model rejected, so we stop sending them


def _create(client, model: str, messages: list):
    """One model call. Drops temperature or JSON mode if this model does not support them."""
    kwargs = {"model": model, "messages": messages, "tools": TOOLS,
              "temperature": 0, "response_format": {"type": "json_object"}}
    for key in _unsupported:
        kwargs.pop(key, None)
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        # A 400 error naming one of these settings means this model does not accept it.
        if getattr(exc, "status_code", None) == 400:
            for key in ("temperature", "response_format"):
                if key in kwargs and key in str(exc):
                    _unsupported.add(key)
                    print(f"  note: {model} does not accept '{key}'; continuing without it")
                    return _create(client, model, messages)
        raise


# ---------------------------------------------------------------- checks on the answer

def _numbers(text: str) -> list[tuple[float, int]]:
    """Numbers written in text, with how many decimals were written."""
    found = []
    for raw in NUMBER.findall(text):
        raw = raw.rstrip(",").replace(",", "")
        if not raw:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        found.append((abs(float(raw)), decimals))
    return found


def ungrounded_numbers(note: str, tool_results: list[dict]) -> list[str]:
    """Numbers in the note that no tool returned (allowing for rounding as written)."""
    source = [n for r in tool_results for n, _ in _numbers(json.dumps(r))]
    missing = []
    for value, decimals in _numbers(note):
        if value in INSTRUCTION_NUMBERS:
            continue
        if not any(math.isclose(round(s, decimals), value, abs_tol=1e-9) for s in source):
            missing.append(f"{value:.{decimals}f}")
    return missing


def _parse_answer(content: str | None) -> dict | None:
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------- the loop

def triage(exception_id: str, client=None, model: str | None = None, verbose: bool = False) -> dict:
    """Classify one exception. Returns the answer plus a full trace of every step."""
    client = client or get_client()
    model = model or MODEL
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Triage exception {exception_id}."}]
    steps, tool_results = [], []
    usage = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
    forced_reason, answer = None, None

    def add_usage(response) -> None:
        if response.usage:
            usage["input_tokens"] += response.usage.prompt_tokens
            usage["output_tokens"] += response.usage.completion_tokens
            details = getattr(response.usage, "prompt_tokens_details", None)
            usage["cached_tokens"] += (getattr(details, "cached_tokens", 0) or 0) if details else 0

    while True:
        response = _create(client, model, messages)
        add_usage(response)
        message = response.choices[0].message

        if not message.tool_calls:  # the model has answered
            answer = _parse_answer(message.content)
            steps.append({"step": len(steps) + 1, "final_answer": message.content})
            if verbose:
                print(f"\nFINAL ANSWER:\n{message.content}")
            break

        messages.append({"role": "assistant", "content": message.content, "tool_calls": [
            {"id": c.id, "type": "function",
             "function": {"name": c.function.name, "arguments": c.function.arguments}}
            for c in message.tool_calls]})
        for call in message.tool_calls:
            if len(tool_results) >= MAX_TOOL_CALLS:
                forced_reason = f"asked for more than {MAX_TOOL_CALLS} tool calls"
                break
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(call.function.name, args)
            tool_results.append(result)
            steps.append({"step": len(steps) + 1, "tool": call.function.name,
                          "arguments": args, "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
            if verbose:
                print(f"\n[{len(tool_results)}] {call.function.name}({json.dumps(args)})")
                print(json.dumps(result, indent=2))
        if forced_reason:
            break

    # ---- one repair attempt if the answer used a label that is not allowed
    label_repaired = False
    if not forced_reason and answer is not None and answer.get("break_type") not in LABELS:
        messages.append({"role": "assistant", "content": message.content})
        messages.append({"role": "user", "content": (
            f"'{answer.get('break_type')}' is not an allowed break_type. Reply with the same JSON, "
            f"with break_type set to exactly one of: {', '.join(LABELS)}.")})
        response = _create(client, model, messages)
        add_usage(response)
        content = response.choices[0].message.content
        steps.append({"step": len(steps) + 1, "label_repair": True, "final_answer": content})
        retry = _parse_answer(content)
        if retry and retry.get("break_type") in LABELS:
            answer, label_repaired = retry, True
        if verbose:
            print(f"\nLABEL REPAIR:\n{content}")

    # ---- checks in code after every answer
    raw_label = (answer or {}).get("break_type")
    label = raw_label if raw_label in LABELS else "unclear"
    if forced_reason:
        label = "unclear"
    elif answer is None:
        forced_reason = "answer was not valid JSON"
    elif raw_label not in LABELS:
        forced_reason = f"invalid label {raw_label!r}"
    note = str((answer or {}).get("note", ""))
    missing = ungrounded_numbers(note, tool_results)
    confidence = (answer or {}).get("confidence")
    cost = (usage["input_tokens"] - usage["cached_tokens"]) * PRICE_INPUT / 1e6 \
        + usage["cached_tokens"] * PRICE_CACHED / 1e6 + usage["output_tokens"] * PRICE_OUTPUT / 1e6

    return {
        "exception_id": exception_id,
        "break_type": label,
        "confidence": confidence if confidence in ("high", "medium", "low") else "low",
        "evidence": (answer or {}).get("evidence", []),
        "note": note,
        "grounded": not missing,
        "ungrounded_numbers": missing,
        "forced_unclear": forced_reason,
        "label_repaired": label_repaired,
        "tool_calls": len(tool_results),
        "model": model,
        **usage,
        "cost_usd": round(cost, 6),
        "steps": steps,
    }


# ---------------------------------------------------------------- batch runs

def _paths(split: str, run: int) -> tuple:
    suffix = "" if split == "test" else f"_{split}"
    suffix += "" if run == 1 else f"_run{run}"
    return DATA / f"traces{suffix}.jsonl", DATA / f"predictions_agent{suffix}.csv"


def run_split(split: str, run: int = 1, workers: int = 4, limit: int | None = None,
              client=None, force: bool = False) -> pd.DataFrame:
    traces_path, preds_path = _paths(split, run)
    ids = load_split().query("split == @split")["exception_id"].tolist()
    if limit:
        ids = ids[:limit]
    # The test set is run once. Finishing items that failed (e.g. an API error) is allowed;
    # running a complete test set again is not, unless --force.
    if split == "test" and preds_path.exists() and not force:
        answered = set(pd.read_csv(preds_path)["exception_id"])
        if answered >= set(ids):
            sys.exit(f"{preds_path.name} is complete: the test set is run once. "
                     "Use --force only if you truly mean to overwrite it.")
    if force:
        traces_path.unlink(missing_ok=True)
    done = set()
    if traces_path.exists():  # resume an interrupted run
        done = {json.loads(line)["exception_id"] for line in traces_path.read_text(encoding="utf-8").splitlines() if line}
    todo = [i for i in ids if i not in done]
    print(f"{split} set: {len(ids)} exceptions, {len(done & set(ids))} already done, {len(todo)} to run "
          f"with {MODEL} ({workers} at a time)")

    client = client or get_client()
    lock = threading.Lock()
    started = time.time()
    finished = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(triage, i, client): i for i in todo}
        for future in as_completed(futures):
            exception_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                name = type(exc).__name__
                if name in ("AuthenticationError", "PermissionDeniedError", "NotFoundError") or "insufficient_quota" in str(exc):
                    pool.shutdown(cancel_futures=True)
                    sys.exit(f"\nStopped: {name}: {exc}\nFinished items are saved; re-run the same "
                             "command to continue once the key or credit is fixed.")
                print(f"  {exception_id}: failed ({name}: {exc}); re-run the command to retry it")
                continue
            with lock:
                with traces_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")
                finished += 1
                if finished % 25 == 0 or finished == len(todo):
                    print(f"  {finished}/{len(todo)} done ({time.time() - started:.0f}s)")

    records = [json.loads(line) for line in traces_path.read_text(encoding="utf-8").splitlines() if line]
    records = [r for r in records if r["exception_id"] in set(ids)]
    preds = pd.DataFrame([{k: r[k] for k in ("exception_id", "break_type", "confidence", "grounded",
                                             "tool_calls", "cost_usd")} for r in records])
    preds = preds.rename(columns={"break_type": "predicted_type"}).sort_values("exception_id")
    write_csv(preds, preds_path)

    spend = preds["cost_usd"].sum()
    print(f"\nSaved {len(preds)} predictions -> {preds_path.name}, traces -> {traces_path.name}")
    print(f"Estimated spend this set: ${spend:.4f} (${spend / max(len(preds), 1):.5f} per exception)")
    if len(preds) < len(ids):
        print(f"{len(ids) - len(preds)} still missing: re-run the same command to finish them.")
    return preds


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the reconciliation triage agent.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--one", metavar="EXCEPTION_ID", help="triage one exception, printing every step")
    group.add_argument("--split", choices=["dev", "test"], help="triage every exception in a split")
    parser.add_argument("--run", type=int, default=1, help="run number (use 2 for the dev stability check)")
    parser.add_argument("--workers", type=int, default=4, help="exceptions processed at the same time")
    parser.add_argument("--limit", type=int, help="only the first N exceptions of the split")
    parser.add_argument("--force", action="store_true", help="overwrite an existing run")
    args = parser.parse_args()

    if args.one:
        result = triage(args.one, verbose=True)
        print("\nCHECKED RESULT:")
        print(json.dumps({k: v for k, v in result.items() if k != "steps"}, indent=2))
    else:
        run_split(args.split, run=args.run, workers=args.workers, limit=args.limit, force=args.force)


if __name__ == "__main__":
    main()
