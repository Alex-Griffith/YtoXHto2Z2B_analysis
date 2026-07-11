# Current resonant analysis audit

## Scope

This audit describes the code as read before background-production changes.
The reconstructed lepton and jet selections are not changed by the background
infrastructure work.

## Existing selection

The processor first resolves data/MC status and NanoAOD branch compatibility.
It then evaluates the configured trigger OR, constructs the no-FSR
`H -> ZZ(*) -> 4l` candidate, selects cleaned AK4 PUPPI jets, and ranks the
jets by the first available configured b-tag branch.

The HZZ path applies, in order:

1. at least four selected electrons/muons;
2. OS-SF Z candidates with `12 < mll < 120 GeV`;
3. pairwise lepton `deltaR > 0.02`;
4. leading/subleading lepton `pT > 20/10 GeV`;
5. every opposite-sign lepton pair has mass above 4 GeV;
6. Z1 is the candidate closest to the Z mass and has mass above 40 GeV;
7. the same-flavour alternate-pair smart-cut helper;
8. `mZ1 + mZ2 > 70 GeV`.

Jets require `pT > 20 GeV`, `|eta| < 2.4`, configured JetID, and
`deltaR(jet, tight lepton) >= 0.4`. The two highest b-tag-score cleaned jets
form the bb candidate. There is currently no b-tag working-point requirement
and no bb mass window.

The existing baseline is:

`trigger && pass_hzz4l_candidate && at_least_two_clean_jets`

The existing signal-region flag adds only `105 < mass4l < 160 GeV`.

## Output contents

The ROOT `Events` tree contains one row per processed input event. Existing
branches include run/luminosityBlock/event, genWeight, selection flags,
mass4l, massZ1, massZ2, four selected lepton vectors, two selected jet
vectors and b-tag values, massbb, massbb4l, jet multiplicity, MET, and signal
mass hypotheses. Missing candidates use `-99` defaults.

The JSON stores the input list, resolved sample type, NanoAOD compatibility,
schema warnings, the original diagnostic cutflow, configuration snapshot and
selected-observable summaries.

## Background-readiness gaps found

Before this audit the output had no sample name/process group/year/dataset
metadata, no cross section, no luminosity, no dataset sumGenWeight, and no
sequential weighted cutflow. Therefore raw selected counts could not be used
to rank backgrounds.

The additive background-readiness update preserves every existing selection
decision and existing output branch. It adds:

- a separate sequential cutflow;
- sums of genWeight and genWeight squared at every sequential stage;
- optional sample and normalization metadata;
- explicit normalization status instead of silently assuming xsec=1;
- `baseEventWeight` and `normalizedWeight` branches;
- `SequentialCutflow` and `SampleMetadata` ROOT objects.

When cross section, luminosity or full-dataset sumGenWeight is missing, the
normalized weight remains unavailable (`-99` in the event tree) and the JSON
lists the missing fields. This is intentional.
