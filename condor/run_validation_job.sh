#!/bin/bash
set -euo pipefail

if [ "$#" -lt 6 ]; then
  echo "Usage: $0 SAMPLE_NAME SAMPLE_TYPE NANOAOD_VERSION INPUT_FILE MAX_EVENTS JOB_INDEX"
  exit 2
fi

SAMPLE_NAME=$1
SAMPLE_TYPE=$2
NANOAOD_VERSION=$3
INPUT_FILE=$4
MAX_EVENTS=$5
JOB_INDEX=$6

REPO_DIR=${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
OUTPUT_DIR="${REPO_DIR}/outputs/validation/${SAMPLE_NAME}"
mkdir -p "${OUTPUT_DIR}"

JSON_OUTPUT="${OUTPUT_DIR}/${SAMPLE_NAME}_${JOB_INDEX}.json"
ROOT_OUTPUT="${OUTPUT_DIR}/${SAMPLE_NAME}_${JOB_INDEX}.root"
if [ -e "${JSON_OUTPUT}" ] || [ -e "${ROOT_OUTPUT}" ]; then
  echo "Refusing to overwrite existing outputs: ${JSON_OUTPUT} ${ROOT_OUTPUT}" >&2
  exit 3
fi

export SAMPLE_TYPE
export NANOAOD_VERSION
if [ "${MAX_EVENTS}" != "0" ] && [ "${MAX_EVENTS}" != "-1" ]; then
  export MAX_EVENTS
else
  unset MAX_EVENTS
fi

cd "${REPO_DIR}"
scripts/run_analysis.sh "${INPUT_FILE}" "${JSON_OUTPUT}" "${ROOT_OUTPUT}"
