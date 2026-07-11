# Validation Summary

This document records the first-pass NanoAOD compatibility validation for the standalone `YtoXHto2Z2B_analysis` repository.

## Source Samples

| sample | type | version | source |
| --- | --- | --- | --- |
| v15 HH bb4l | MC | v15 | requested official NanoAODv15 sanity-test file in `filelists/v15_hhbb4l_test.txt` |
| v12 HH bb4l | MC | v12 | old Condor JDL `submit_condor_jobs_lnujj_Run3_Signal_2022.jdl` |
| v12 ZZ4l | MC | v12 | old `input_data_Files/sample_list_v12_2022.dat`; files expanded from DAS |
| v12 TTZ-ZtoQQ technical check | MC | v12 | branch/schema smoke test only; not a physics background for the 4l analysis |
| v12 data | data | v12 | old `input_data_Files/sample_list_v12_2022.dat`; files expanded from `/MuonEG/Run2022E-22Sep2023-v1/NANOAOD` |

The old `samples_Bkg_TTV.txt` entries named `TTZToLL_M-*` did not return files from DAS during this pass. The available Run3Summer22 NanoAODv12 `TTZ-ZtoQQ-1Jets` file was used only to exercise the v12 branch/schema path. It is deliberately excluded from `configs/background_samples.json` and must not be submitted as the ttZ background for this 4l analysis.

## Smoke Tests

Run locally on lxplus:

```bash
MAX_EVENTS=100 SAMPLE_TYPE=mc NANOAOD_VERSION=v12 scripts/run_analysis.sh filelists/v12_hhbb4l_test.txt outputs/smoke/v12_hhbb4l.json outputs/smoke/v12_hhbb4l.root
MAX_EVENTS=100 SAMPLE_TYPE=mc NANOAOD_VERSION=v12 scripts/run_analysis.sh filelists/v12_zz4l_test.txt outputs/smoke/v12_zz4l.json outputs/smoke/v12_zz4l.root
MAX_EVENTS=100 SAMPLE_TYPE=mc NANOAOD_VERSION=v12 scripts/run_analysis.sh filelists/v12_ttz_test.txt outputs/smoke/v12_ttz.json outputs/smoke/v12_ttz.root
MAX_EVENTS=100 SAMPLE_TYPE=data NANOAOD_VERSION=v12 scripts/run_analysis.sh filelists/v12_data_test.txt outputs/smoke/v12_data.json outputs/smoke/v12_data.root
MAX_EVENTS=100 SAMPLE_TYPE=mc NANOAOD_VERSION=v15 scripts/run_analysis.sh filelists/v15_hhbb4l_test.txt outputs/smoke/v15_hhbb4l.json outputs/smoke/v15_hhbb4l.root
```

## Condor Dry Run

Prepare a small first-pass submission without submitting:

```bash
export X509_USER_PROXY=/afs/cern.ch/user/b/bfan/x509up_u174944
scripts/submit_validation.py v12_zz4l mc v12 filelists/v12_zz4l_test.txt --max-events 50000 --max-jobs 3
```

The submit template requests forwarding of the active X.509 proxy. The script prints the exact `condor_submit` command and job count. Add `--submit` only after reviewing the generated command and checking `voms-proxy-info --timeleft`.

The dry run prepared 3 jobs and printed:

```bash
condor_submit /eos/home-b/bfan/YtoXHto2Z2B_analysis/condor/generated/v12_zz4l.sub -append sample_name=v12_zz4l -append sample_type=mc -append nanoaod_version=v12 -append max_events=50000 -append job_flavour=workday -append queue_file=/eos/home-b/bfan/YtoXHto2Z2B_analysis/condor/generated/v12_zz4l.queue
```

No Condor jobs were submitted during this validation pass.

## Plots

Create validation-only plots from smoke-test output ROOT files:

```bash
scripts/make_validation_plots.py \
  outputs/smoke/v12_hhbb4l.root outputs/smoke/v12_zz4l.root \
  outputs/smoke/v12_ttz.root outputs/smoke/v12_data.root \
  outputs/smoke/v15_hhbb4l.root -o plots/validation/smoke
```

Plots are validation-only: no luminosity normalization, scale factors, or systematic treatment is applied.
All 11 requested plots were produced as PNG and PDF for each of the 5 samples (110 non-empty files total).

## Smoke-Test Results

| sample | events | trigger | pass ZZ | two jets | baseline | b-tag branch | JetID | truth | missing HLT |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| v12 HH bb4l | 100 | 84 | 12 | 81 | 8 | `Jet_btagPNetB` | input `Jet_jetId` | on | none |
| v12 ZZ4l | 100 | 39 | 2 | 22 | 0 | `Jet_btagPNetB` | input `Jet_jetId` | on | none |
| v12 TTZ-ZtoQQ technical check | 100 | 26 | 0 | 100 | 0 | `Jet_btagPNetB` | input `Jet_jetId` | on | none |
| v12 data | 100 | 26 | 0 | 84 | 0 | `Jet_btagPNetB` | input `Jet_jetId` | off | none |
| v15 HH bb4l | 100 | 85 | 18 | 90 | 16 | `Jet_btagUParTAK4B` | recomputed Tight | on | none |

Here `baseline` is `trigger && passZZ && passTwoJets`. The 100-event TTZ-ZtoQQ technical slice and data slice contain no selected 4l candidate; their empty mass plots are therefore expected, while jet and cutflow plots remain populated. The TTZ-ZtoQQ slice is not part of the physics background submission.

## Current Compatibility Notes

- Data must have `truth_matching_enabled = false` and `genWeight = 1`.
- Missing HLT branches should appear only in JSON warnings.
- v12 samples are expected to use the b-tag fallback if `Jet_btagUParTAK4B` is absent.
- `Jet_jetId` is used directly when present; otherwise the existing AK4PUPPI Tight JetID recomputation is used.
- NanoAODv12 contains `Electron_mvaHZZIso` but not `Electron_mvaIso_WPHZZ`. The HZZ working-point boolean is recomputed with the six official Summer18UL category cuts; v15 uses the stored boolean directly. The selected mode is recorded as `schema.electron_hzz_id`.
- No crash, missing-HLT warning, or incomplete truth schema was observed in the five smoke tests. The only warnings were the expected v12 b-tagger fallback and v15 JetID recomputation.
