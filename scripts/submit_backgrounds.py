#!/usr/bin/env python3
"""Validate a prepared queue and optionally submit it to HTCondor."""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json")
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    summary = json.loads(Path(args.summary_json).read_text())
    queue_file = Path(summary["queue_file"])
    if not queue_file.is_absolute():
        queue_file = (repo / queue_file).resolve()
    if not queue_file.is_file() or not queue_file.read_text().strip():
        raise SystemExit(f"Queue file is missing or empty: {queue_file}")

    for sample in summary["samples"]:
        (repo / sample["log_dir"]).mkdir(parents=True, exist_ok=True)
        Path(sample["output_path"]).mkdir(parents=True, exist_ok=True)

    proxy_check = subprocess.run(
        ["voms-proxy-info", "-exists", "-valid", "08:00"], check=False
    )
    if proxy_check.returncode:
        if not args.submit:
            raise SystemExit("No proxy valid for 8 hours; create one before dry-run/submit")
        subprocess.run(["voms-proxy-init", "-voms", "cms", "-valid", "192:00"], check=True)
    source_proxy = subprocess.check_output(
        ["voms-proxy-info", "-path"], text=True
    ).strip()
    proxy_dir = Path("/afs/cern.ch/user/b/bfan/private/condor_proxy")
    proxy_dir.mkdir(parents=True, exist_ok=True)
    proxy_copy = proxy_dir / "x509up_u174944_backgrounds"
    shutil.copyfile(source_proxy, proxy_copy)
    proxy_copy.chmod(0o600)

    env = dict(os.environ, X509_USER_PROXY=str(proxy_copy))
    submit_file = repo / "condor" / "submit_background.sub"
    dry_run_ad = repo / "condor" / "generated" / "backgrounds" / "background_dry_run.ad"
    command = [
        "condor_submit", "-dry-run", str(dry_run_ad),
        f"queue_file={queue_file}", str(submit_file),
    ]
    print("Dry-run command:", " ".join(map(str, command)))
    subprocess.run(command, cwd=repo, env=env, check=True)
    if args.submit:
        real_command = ["condor_submit", f"queue_file={queue_file}", str(submit_file)]
        print("Submit command:", " ".join(map(str, real_command)))
        subprocess.run(real_command, cwd=repo, env=env, check=True)
    else:
        print("Dry-run only. Add --submit after inspecting the ClassAds.")


if __name__ == "__main__":
    main()
