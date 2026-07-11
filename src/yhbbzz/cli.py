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
    parser.add_argument("--sample-name")
    parser.add_argument("--process-group")
    parser.add_argument("--year")
    parser.add_argument("--era")
    parser.add_argument("--dataset")
    parser.add_argument("--cross-section-pb", type=float)
    parser.add_argument("--sum-gen-weight", type=float)
    parser.add_argument("--luminosity-fb", type=float)
    args = parser.parse_args()

    sample_metadata = {
        key: value for key, value in {
            "sample_name": args.sample_name,
            "process_group": args.process_group,
            "year": args.year,
            "era": args.era,
            "dataset": args.dataset,
            "cross_section_pb": args.cross_section_pb,
            "sum_gen_weight": args.sum_gen_weight,
            "luminosity_fb": args.luminosity_fb,
        }.items() if value is not None
    }
    result = run(args.input, args.config, args.output, args.max_events, args.root_output,
                 args.sample_type, args.nanoaod_version, sample_metadata)
    print(json.dumps(result["cutflow"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")
    print(f"Wrote {result['plot_ntuple']}")


if __name__ == "__main__":
    main()
