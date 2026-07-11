#!/usr/bin/env python3
"""Prepare one-file-per-job background queue files without submitting."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def iter_samples(config):
    for category, samples in config["categories"].items():
        for sample in samples:
            yield category, sample


def read_filelist(repo, path):
    values = []
    for line in (repo / path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            values.append(line)
    return values


def field(value):
    return "NONE" if value is None else str(value)


def validate_token(name, value):
    if not value or re.search(r"\s", str(value)):
        raise ValueError(f"{name} must be a non-empty token without whitespace: {value!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/background_samples.json")
    parser.add_argument("--mode", choices=("pilot", "production"), default="pilot")
    parser.add_argument("--samples", help="Comma-separated sample names; default is all first_round samples")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--run-tag")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    config = json.loads((repo / args.config).read_text())
    requested = set(args.samples.split(",")) if args.samples else None
    run_tag = args.run_tag or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    max_files = args.max_files
    if args.mode == "pilot" and max_files is None:
        max_files = 1

    queue_dir = repo / "condor" / "generated" / "backgrounds"
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_file = queue_dir / f"{args.mode}_{run_tag}.queue"
    summary_file = queue_file.with_suffix(".json")
    rows = []
    summary = {"mode": args.mode, "run_tag": run_tag, "samples": [], "warnings": []}

    for category, sample in iter_samples(config):
        name = sample["sample_name"]
        if requested is not None and name not in requested:
            continue
        if requested is None and not sample.get("first_round", False):
            continue
        if not sample.get("filelist"):
            summary["warnings"].append(f"{name}: no filelist; skipped")
            continue
        inputs = read_filelist(repo, sample["filelist"])
        if max_files is not None:
            inputs = inputs[:max_files]
        if not inputs:
            summary["warnings"].append(f"{name}: empty filelist; skipped")
            continue

        output_path = (
            f"/eos/user/b/bfan/YtoXHto2Z2B_analysis/outputs/backgrounds/"
            f"{sample['year']}/{name}/jobs/{run_tag}"
        )
        output_url = f"root://eosuser.cern.ch/{output_path}"
        log_dir = f"logs/backgrounds/{sample['year']}/{name}/{run_tag}"
        for token_name in ("sample_name", "process_group", "sample_type", "year", "era", "nanoaod_version"):
            validate_token(token_name, sample[token_name])
        validate_token("dataset", sample["dataset"])

        for job_index, input_file in enumerate(inputs):
            columns = [
                name, sample["process_group"], sample["sample_type"], sample["year"],
                sample["era"], sample["nanoaod_version"], input_file, output_url,
                args.max_events if args.mode == "pilot" else -1, job_index,
                field(sample["cross_section_pb"]), field(sample["sum_gen_weight"]),
                field(sample["luminosity_fb"]), sample["dataset"], run_tag, log_dir,
            ]
            if any(re.search(r"\s", str(value)) for value in columns):
                raise ValueError(f"Queue fields may not contain whitespace: {columns}")
            rows.append(" ".join(map(str, columns)))

        summary["samples"].append({
            "sample_name": name,
            "category": category,
            "jobs": len(inputs),
            "input_files": len(inputs),
            "max_events": args.max_events if args.mode == "pilot" else -1,
            "output_path": output_path,
            "log_dir": log_dir,
            "normalization_ready": all(sample.get(key) is not None for key in (
                "cross_section_pb", "sum_gen_weight", "luminosity_fb"
            )),
        })

    if not rows:
        raise SystemExit("No runnable samples have filelists")
    queue_file.write_text("\n".join(rows) + "\n")
    summary["queue_file"] = str(queue_file)
    summary["total_jobs"] = len(rows)
    summary_file.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
