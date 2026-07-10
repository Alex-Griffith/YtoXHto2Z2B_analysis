import argparse
import json
from pathlib import Path

from .analysis import run


def main():
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run the minimal YH(bb,4l) NanoAOD analysis")
    parser.add_argument("input", help="Input NanoAOD ROOT file")
    parser.add_argument("-c", "--config", default=str(repo / "configs" / "default.json"))
    parser.add_argument("-o", "--output", default="outputs/cutflow.json")
    parser.add_argument("-r", "--root-output",
                        help="Plotting ROOT ntuple (default: JSON output with .root suffix)")
    parser.add_argument("-n", "--max-events", type=int, default=-1)
    parser.add_argument("--sample-type", choices=("auto", "data", "mc"),
                        help="Input sample type. Use data to disable MC-only branches.")
    parser.add_argument("--nanoaod-version", choices=("auto", "v12", "v15"),
                        help="NanoAOD branch compatibility hint. Branches are still checked dynamically.")
    args = parser.parse_args()

    result = run(args.input, args.config, args.output, args.max_events, args.root_output,
                 args.sample_type, args.nanoaod_version)
    print(json.dumps(result["cutflow"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {result['plot_ntuple']}")


if __name__ == "__main__":
    main()
