# Reuse of old nonresonant HH to bb4l ROOT files

## Inputs inspected

The source directory is read-only for this work:

`/eos/user/b/bfan/CMSSW_13_3_3/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim`

The following representative files were opened with ROOT:

- `skim_reference.root`;
- `skim_with_newSF.root`;
- `temp_skim_output/131cb760-bb6e-4f61-9ca7-85bf566c7aa6_Skim.root`;
- `temp_skim_output/4fb597df-2acd-4ee8-bf4b-3129cd472b47_Skim.root`;
- `temp_skim_output/bf9e5d8e-ef6e-472e-ae09-04dd2ab18bcd_Skim.root`.

The last file is a zombie: ROOT reports that it was not closed and no keys
can be recovered. It must not be used.

## Two distinct old output formats

### Compact H4L output

`skim_reference.root` and `skim_with_newSF.root` each contain 14,728 Events
and 232 branches. They retain event identifiers, genWeight, mass4l, massZ1,
massZ2, selected jet pT/b-tag values, `invjj`, old selection flags and several
weight branches. They do not retain the full Electron or Jet collections and
do not contain massbb4l.

Classification: **partial reuse (B)**. These files can support comparisons
using the already-built old candidates and old selection, but they cannot be
used to rerun the current object selection or reconstruct all resonant
observables.

### Broad NanoAOD-like skim

The usable files under `temp_skim_output` contain about 1,702 branches,
including full Electron, Muon and Jet collections, HLT, genWeight, PNet and
DeepFlavour b-tag values, and the NanoAOD Runs/LuminosityBlocks trees. The old
MC PostProcessor prefilter was only:

`raw electron count + raw muon count >= 4 && raw nJet >= 2`

Those are necessary conditions for the current resolved baseline. The files
can therefore be fed through the current selection at much lower I/O cost.

Classification: **partial reuse (B)** rather than unconditional A, for two
reasons:

1. file names are input UUIDs and currently lack a reliable sample/dataset
   manifest;
2. the skim Runs tree reports the skimmed count/sumGenWeight, not a proven
   full-dataset normalization denominator.

They are suitable for selection compatibility, shapes and raw cutflows. They
become suitable for luminosity-normalized yields only after each UUID is
mapped to its dataset and the full dataset sumGenWeight is supplied externally.

## Old weight caveat

The old `H4LCppModule.py` defines:

`Weight = genWeight * dataMCWeight_new * prefiringWeight`

In the inspected implementation, `dataMCWeight_new` and `prefiringWeight` are
initialized to one and no assignment that changes them was found. A separate
pileup weight may be present, but it is not multiplied into `Weight` there.
Consequently the old `Weight` branch must not be described as a complete
pileup/lepton/trigger/b-tag corrected event weight without further evidence.

## Reuse decision

- Use valid broad `temp_skim_output` files first for cheap compatibility and
  raw-background studies after building a UUID-to-dataset manifest.
- Use compact H4L files only for old-vs-new candidate/selection comparisons.
- Do not use zombie ROOT files.
- Do not use any old skim for a normalized yield until xsec, luminosity and
  full-sample sumGenWeight are independently documented.
