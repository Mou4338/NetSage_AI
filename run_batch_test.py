"""
NetSage AI - batch test harness
Runs every row of a labeled test set (cases.csv) through the same
rule-checker -> Gemini pipeline the app uses, then scores the AI's
diagnosis against the known-correct answer. This is your "testing"
evidence for the project submission.

Usage:
    python run_batch_test.py cases.csv
    python run_batch_test.py cases.csv --limit 5      # quick smoke test
    python run_batch_test.py cases.csv --out results.csv

Expects cases.csv with columns:
    case_id, concept_tag, severity, osi_layer, symptom, topology_note, show_output, expected_fault
"""
import argparse
import os
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from netsage_core import DEFAULT_SYSTEM_PROMPT, run_rule_checker, build_user_prompt, extract_json

from google import genai
from google.genai import types

PROMPT_PATH = "diagnose_prompt.md"
CASE_LOG_PATH = "netsage_case_log.csv"  # same file app.py's Dashboard tab reads

# cases.csv uses its own concept_tag vocabulary; map it onto the app's Category dropdown
CONCEPT_TO_CATEGORY = {
    "VLAN": "VLAN", "GATEWAY": "IP Addressing", "DHCP": "DHCP", "DNS": "Other",
    "ROUTING": "Routing", "ACL": "NAT/ACL", "NAT": "NAT/ACL", "WIRELESS": "Physical",
}


def seed_dashboard(row, diagnosis, layer_match):
    """Append this batch-test result to netsage_case_log.csv so it shows up
    in the Dashboard tab, tagged with source=batch_test so you can tell it
    apart from cases you actually reviewed by hand."""
    new_row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "symptom": row.get("symptom"),
        "category": CONCEPT_TO_CATEGORY.get(str(row.get("concept_tag")).upper(), "Other"),
        "severity": row.get("severity"),
        "osi_layer": diagnosis.get("osi_layer"),
        "confidence": diagnosis.get("confidence"),
        "root_cause": diagnosis.get("root_cause"),
        "feedback": "accepted" if layer_match else "rejected",
        "source": "batch_test",
    }
    if os.path.exists(CASE_LOG_PATH):
        existing = pd.read_csv(CASE_LOG_PATH)
        combined = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
    else:
        combined = pd.DataFrame([new_row])
    combined.to_csv(CASE_LOG_PATH, index=False)


def merge_and_write(new_results, out_path):
    """Combine this run's results with whatever's already in out_path, instead
    of blowing the file away. Any case_id being (re)run now replaces its old
    row; every other existing row (e.g. cases before --start-id, or cases
    from an earlier day) is kept as-is."""
    new_df = pd.DataFrame(new_results)
    existing = pd.DataFrame()
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        try:
            existing = pd.read_csv(out_path)
        except pd.errors.EmptyDataError:
            existing = pd.DataFrame()  # file existed but had no parseable rows — treat as empty
    if not existing.empty and "case_id" in existing.columns:
        new_ids = set(new_df["case_id"]) if not new_df.empty and "case_id" in new_df.columns else set()
        existing = existing[~existing["case_id"].isin(new_ids)]
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    if "case_id" in combined.columns:
        combined = combined.sort_values("case_id", kind="stable")
    combined.to_csv(out_path, index=False)
    return combined


def load_system_prompt():
    if os.path.exists(PROMPT_PATH):
        return open(PROMPT_PATH).read()
    return DEFAULT_SYSTEM_PROMPT


def run_one(client, model_name, system_prompt, row):
    findings = run_rule_checker(row["show_output"])
    user_prompt = build_user_prompt(row["symptom"], row["topology_note"], row["show_output"], findings)
    response = client.models.generate_content(
        model=model_name,
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=types.GenerateContentConfig(max_output_tokens=2000, temperature=0.0),
    )
    diagnosis = extract_json(response.text)
    return findings, diagnosis


def score_row(row, diagnosis):
    """Loose scoring: does the predicted OSI layer match, and does the
    predicted root cause mention any keyword from the expected fault?"""
    layer_match = str(diagnosis.get("osi_layer", "")).strip().upper() == str(row["osi_layer"]).strip().upper()

    expected_words = set(w.strip(".,()-").lower() for w in str(row["expected_fault"]).split() if len(w) > 4)
    predicted_text = (str(diagnosis.get("root_cause", "")) + " " + str(diagnosis.get("evidence", ""))).lower()
    keyword_hits = sum(1 for w in expected_words if w in predicted_text)
    keyword_overlap = keyword_hits / max(len(expected_words), 1)

    return layer_match, round(keyword_overlap, 2)


def main():
    parser = argparse.ArgumentParser(description="Batch-test NetSage AI against a labeled case set")
    parser.add_argument("infile", help="path to cases.csv")
    parser.add_argument("--out", default="batch_test_results.csv", help="path to write results CSV")
    parser.add_argument("--limit", type=int, default=None, help="only run the first N cases (for a quick smoke test)")
    parser.add_argument("--model", default=None, help="override model name (else reads NETSAGE_MODEL from .env)")
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds to sleep between API calls (rate limiting)")
    parser.add_argument("--seed-dashboard", action="store_true",
                         help="also append each result to netsage_case_log.csv so it shows up in the app's Dashboard tab")
    parser.add_argument("--resume", action="store_true",
                         help="skip case_ids that already succeeded in --out from a previous run (use after hitting a daily quota)")
    parser.add_argument("--start-id", default=None,
                         help="skip every case before this case_id (e.g. --start-id C022 runs C022 onward, in cases.csv's row order)")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found — create a .env file with GOOGLE_API_KEY=your_key_here")
    client = genai.Client(api_key=api_key)

    model_name = args.model or os.environ.get("NETSAGE_MODEL", "gemini-3.6-flash")
    system_prompt = load_system_prompt()

    df = pd.read_csv(args.infile)
    if args.limit:
        df = df.head(args.limit)

    if args.start_id:
        ids = df["case_id"].astype(str).tolist()
        if args.start_id not in ids:
            raise SystemExit(f"--start-id {args.start_id} not found in {args.infile}. Available ids: {ids}")
        start_pos = ids.index(args.start_id)
        skipped = df.iloc[:start_pos]
        df = df.iloc[start_pos:]
        print(f"--start-id {args.start_id}: skipping {len(skipped)} earlier case(s), running {len(df)} case(s).")

    already_done = set()
    results = []
    if args.resume and os.path.exists(args.out):
        prev = pd.read_csv(args.out)
        succeeded = prev[prev["error"].astype(str) == ""]
        already_done = set(succeeded["case_id"])
        print(f"Resuming: {len(already_done)} case(s) already succeeded in {args.out} and will be skipped.")

    for i, row in df.iterrows():
        case_id = row.get("case_id", i)
        if case_id in already_done:
            continue
        print(f"[{case_id}] running...", end=" ", flush=True)
        try:
            findings, diagnosis = run_one(client, model_name, system_prompt, row)
            layer_match, keyword_overlap = score_row(row, diagnosis)
            if args.seed_dashboard:
                seed_dashboard(row, diagnosis, layer_match)
            results.append({
                "case_id": case_id,
                "concept_tag": row.get("concept_tag"),
                "expected_osi_layer": row.get("osi_layer"),
                "predicted_osi_layer": diagnosis.get("osi_layer"),
                "layer_match": layer_match,
                "expected_fault": row.get("expected_fault"),
                "predicted_root_cause": diagnosis.get("root_cause"),
                "keyword_overlap": keyword_overlap,
                "confidence": diagnosis.get("confidence"),
                "rule_checker_findings": len(findings),
                "error": "",
            })
            print(f"layer_match={layer_match} overlap={keyword_overlap}")
        except Exception as e:
            err_text = str(e)
            results.append({
                "case_id": case_id, "concept_tag": row.get("concept_tag"),
                "expected_osi_layer": row.get("osi_layer"), "predicted_osi_layer": None,
                "layer_match": False, "expected_fault": row.get("expected_fault"),
                "predicted_root_cause": None, "keyword_overlap": 0.0,
                "confidence": None, "rule_checker_findings": None, "error": err_text,
            })
            print(f"FAILED: {e}")
            if "GenerateRequestsPerDayPerProjectPerModel" in err_text or "PerDay" in err_text:
                combined = merge_and_write(results, args.out)
                print("\nThis is a DAILY quota limit, not a per-minute one — waiting longer won't help today.")
                print(f"Results merged into {args.out} ({len(combined)} case(s) total on file, nothing overwritten).")
                print("Once your quota resets (usually midnight Pacific Time), re-run with --resume to continue:")
                print(f"  python run_batch_test.py {args.infile} --seed-dashboard --resume")
                return
        time.sleep(args.sleep)

    out_df = merge_and_write(results, args.out)

    total = len(out_df)
    layer_acc = out_df["layer_match"].mean() * 100 if total else 0
    avg_overlap = out_df["keyword_overlap"].mean() * 100 if total else 0
    failures = (out_df["error"].astype(str) != "").sum()

    print("\n--- Summary (all cases currently in the output file) ---")
    print(f"Cases run:              {total}")
    print(f"OSI layer accuracy:     {layer_acc:.1f}%")
    print(f"Avg root-cause overlap: {avg_overlap:.1f}%")
    print(f"API/parse failures:     {failures}")
    print(f"Full results written to {args.out} (merged, not overwritten)")

    if "concept_tag" in out_df.columns:
        print("\nAccuracy by concept:")
        by_concept = out_df.groupby("concept_tag")["layer_match"].mean() * 100
        for concept, acc in by_concept.items():
            print(f"  {concept:12} {acc:.0f}%")


if __name__ == "__main__":
    main()
