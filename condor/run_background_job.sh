#!/bin/bash
set -euo pipefail

if [ "$#" -ne 15 ]; then
  echo "Usage: $0 SAMPLE GROUP TYPE YEAR ERA NANO INPUT OUTPUT_URL MAX_EVENTS JOB_INDEX XSEC SUMW LUMI DATASET RUN_TAG" >&2
  exit 2
fi

SAMPLE_NAME=$1
PROCESS_GROUP=$2
SAMPLE_TYPE=$3
YEAR=$4
ERA=$5
NANOAOD_VERSION=$6
INPUT_FILE=$7
OUTPUT_URL=$8
MAX_EVENTS=$9
JOB_INDEX=${10}
CROSS_SECTION_PB=${11}
SUM_GEN_WEIGHT=${12}
LUMINOSITY_FB=${13}
DATASET=${14}
RUN_TAG=${15}

printf 'host=%s\ndate_utc=%s\njob_index=%s\ninput=%s\nsample=%s\nprocess_group=%s\nsample_type=%s\nyear=%s\nera=%s\nnanoaod_version=%s\nrun_tag=%s\n' \
  "$(hostname -f)" "$(date -u --iso-8601=seconds)" "${JOB_INDEX}" "${INPUT_FILE}" \
  "${SAMPLE_NAME}" "${PROCESS_GROUP}" "${SAMPLE_TYPE}" "${YEAR}" "${ERA}" \
  "${NANOAOD_VERSION}" "${RUN_TAG}"

SCRATCH=${_CONDOR_SCRATCH_DIR:-${PWD}}
REPO_DIR=${REPO_DIR:-${SCRATCH}}
SCRAM_ARCH=${SCRAM_ARCH:-el9_amd64_gcc12}
CMSSW_RELEASE=${CMSSW_RELEASE:-/cvmfs/cms.cern.ch/${SCRAM_ARCH}/cms/cmssw/CMSSW_13_3_3}
cd "${SCRATCH}"

set +u
source /cvmfs/cms.cern.ch/cmsset_default.sh
export SCRAM_ARCH
test -d "${CMSSW_RELEASE}"
cd "${CMSSW_RELEASE}"
eval "$(scram runtime -sh)"
set -u
cd "${SCRATCH}"

export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - "${INPUT_FILE}" <<'PY'
import ROOT
import sys

source = ROOT.TFile.Open(sys.argv[1])
if not source or source.IsZombie():
    raise RuntimeError(f"Cannot open input ROOT file: {sys.argv[1]}")
events = source.Get("Events")
if not events:
    raise RuntimeError("Input ROOT file does not contain an Events tree")
print(f"input_entries={events.GetEntries()}")
source.Close()
PY

JOB_LABEL=$(printf '%s_job%04d' "${SAMPLE_NAME}" "${JOB_INDEX}")
LOCAL_JSON="${SCRATCH}/${JOB_LABEL}.json"
LOCAL_ROOT="${SCRATCH}/${JOB_LABEL}.root"

ARGS=(
  "${INPUT_FILE}"
  --config "${REPO_DIR}/configs/default.json"
  --output "${LOCAL_JSON}"
  --root-output "${LOCAL_ROOT}"
  --sample-type "${SAMPLE_TYPE}"
  --nanoaod-version "${NANOAOD_VERSION}"
  --sample-name "${SAMPLE_NAME}"
  --process-group "${PROCESS_GROUP}"
  --year "${YEAR}"
  --era "${ERA}"
  --dataset "${DATASET}"
)
if [ "${MAX_EVENTS}" != "0" ] && [ "${MAX_EVENTS}" != "-1" ]; then
  ARGS+=(--max-events "${MAX_EVENTS}")
fi
if [ "${CROSS_SECTION_PB}" != "NONE" ]; then
  ARGS+=(--cross-section-pb "${CROSS_SECTION_PB}")
fi
if [ "${SUM_GEN_WEIGHT}" != "NONE" ]; then
  ARGS+=(--sum-gen-weight "${SUM_GEN_WEIGHT}")
fi
if [ "${LUMINOSITY_FB}" != "NONE" ]; then
  ARGS+=(--luminosity-fb "${LUMINOSITY_FB}")
fi

python3 -m yhbbzz.cli "${ARGS[@]}"

test -s "${LOCAL_JSON}"
test -s "${LOCAL_ROOT}"
python3 - "${LOCAL_JSON}" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
for key in ("cutflow", "sequential_cutflow", "sample_metadata", "normalization"):
    if key not in payload:
        raise RuntimeError(f"Missing required JSON key: {key}")
print("json_validation=OK")
PY

xrdcp --force --cksum adler32 "${LOCAL_ROOT}" "${OUTPUT_URL}/${JOB_LABEL}.root"
xrdcp --force --cksum adler32 "${LOCAL_JSON}" "${OUTPUT_URL}/${JOB_LABEL}.json"
echo "SUCCESS sample=${SAMPLE_NAME} job_index=${JOB_INDEX} output=${OUTPUT_URL}"
