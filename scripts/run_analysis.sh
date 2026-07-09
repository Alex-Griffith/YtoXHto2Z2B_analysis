#!/bin/bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 INPUT.root [OUTPUT.json]"
  exit 2
fi

REPO_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INPUT=$1
OUTPUT=${2:-${REPO_DIR}/outputs/cutflow.json}
CMSSW_RELEASE=${CMSSW_RELEASE:-/eos/user/b/bfan/YtoXHto2Z2B_MC_generation/CMSSW_15_0_15}

source /cvmfs/cms.cern.ch/cmsset_default.sh
cd "${CMSSW_RELEASE}"
eval "$(scram runtime -sh)"
cd "${REPO_DIR}"

export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
python3 -m yhbbzz.cli "${INPUT}" -o "${OUTPUT}"

