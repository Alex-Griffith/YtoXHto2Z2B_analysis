#!/usr/bin/env python3
"""Show live and historical status for one or more background clusters."""

import argparse
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cluster_ids", nargs="+")
    args = parser.parse_args()
    for cluster_id in args.cluster_ids:
        print(f"=== cluster {cluster_id}: live ===")
        subprocess.run([
            "condor_q", cluster_id, "-af", "ClusterId", "ProcId", "JobStatus",
            "ExitCode", "NumJobStarts", "HoldReason",
        ], check=False)
        print(f"=== cluster {cluster_id}: history ===")
        subprocess.run([
            "condor_history", cluster_id, "-limit", "10000", "-af", "ClusterId",
            "ProcId", "JobStatus", "ExitCode", "NumJobStarts", "HoldReason",
        ], check=False)


if __name__ == "__main__":
    main()
