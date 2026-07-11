#!/usr/bin/env python3
"""Create small HTCondor validation submissions for NanoAOD compatibility tests."""

import argparse
import shlex
import subprocess
from pathlib import Path


def read_inputs(path):
    inputs = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        inputs.append(line)
    return inputs


def write_queue_file(path, inputs, max_jobs):
    selected = inputs if max_jobs is None else inputs[:max_jobs]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(selected) + "\n")
    return len(selected)


def main():
    parser = argparse.ArgumentParser(description="Prepare a small validation Condor submission")
    parser.add_argument("sample_name")
    parser.add_argument("sample_type", choices=("data", "mc"))
    parser.add_argument("nanoaod_version", choices=("v12", "v15", "auto"))
    parser.add_argument("input_filelist")
    parser.add_argument("--max-events", type=int, default=0,
                        help="Events per job. Use 0 to process the full input file.")
    parser.add_argument("--max-jobs", type=int, default=3,
                        help="Limit submitted jobs for first-pass validation.")
    parser.add_argument("--job-flavour", default="workday")
    parser.add_argument("--submit-file", default=None)
    parser.add_argument("--submit", action="store_true",
                        help="Actually run condor_submit. Default is dry-run only.")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    inputs = read_inputs(args.input_filelist)
    if not inputs:
        raise SystemExit(f"No inputs found in {args.input_filelist}")

    queue_file = repo / "condor" / "generated" / f"{args.sample_name}.queue"
    n_jobs = write_queue_file(queue_file, inputs, args.max_jobs)
    submit_file = Path(args.submit_file) if args.submit_file else repo / "condor" / "generated" / f"{args.sample_name}.sub"
    submit_file.parent.mkdir(parents=True, exist_ok=True)

    template = (repo / "condor" / "submit_validation.sub").read_text()
    submit_file.write_text(template)
    (repo / "logs" / "validation" / args.sample_name).mkdir(parents=True, exist_ok=True)
    (repo / "outputs" / "validation" / args.sample_name).mkdir(parents=True, exist_ok=True)

    command = [
        "condor_submit",
        str(submit_file),
        "-append", f"sample_name={args.sample_name}",
        "-append", f"sample_type={args.sample_type}",
        "-append", f"nanoaod_version={args.nanoaod_version}",
        "-append", f"max_events={args.max_events}",
        "-append", f"job_flavour={args.job_flavour}",
        "-append", f"queue_file={queue_file}",
    ]

    print(f"Prepared {n_jobs} validation jobs for sample '{args.sample_name}'.")
    print("Command:")
    print(" ".join(shlex.quote(part) for part in command))
    if args.submit:
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
