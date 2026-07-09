# YtoXHto2Z2B analysis

Standalone analysis code for

`pp -> X(45) -> Y(35) H(25), Y -> bb, H -> ZZ(*) -> 4l`.

The repository is intentionally separate from a CMSSW source area.  CMSSW is
only used as a runtime provider for ROOT; the repository itself is the only
analysis payload that needs to be versioned or sent to a batch worker.

## First working stage

The initial processor performs no signal optimization.  It records independent
truth, trigger, reconstructed-lepton and resolved-jet cutflows, so later cut
changes can be measured rather than guessed.

The `H(25) -> ZZ(*) -> 4l` selection is a no-FSR Python port of the latest
lwang046 H4LTools logic: Run-3 lepton IDs, isolation, OS-SF Z construction,
ghost removal, 20/10 GeV lepton requirements, low-mass OS-pair rejection and
Z1/Z2 choice.  MELA discriminants and the FSR cross-check remain isolated
follow-up validation items.

The current private NanoAODSIM lacks `Jet_jetId`, as expected by the v15
analysis path.  The processor recomputes official AK4PUPPI Tight JetID from the
JME correction JSON, cleans jets against tight leptons, and ranks the remaining
jets with `Jet_btagUParTAK4B` to form the resolved Y candidate.

Run locally:

```bash
scripts/run_analysis.sh \
  /eos/user/b/bfan/YtoXHto2Z2B_MC_generation/condor_nanoaod_1000/20260709T072256Z/job_0000_NANOAODSIM.root \
  outputs/signal_MX1000_MY300.json
```

The default physics and object definitions are in `configs/default.json`.

## Design rules

- PDG 25 is reserved for `H -> ZZ -> 4l`.
- PDG 35 is the configurable `Y -> bb` parent.
- Truth matching is diagnostic and is never required for collision data.
- Mass-point-dependent cuts belong in configuration, not source code.
- Resolved and boosted `Y -> bb` categories will remain separate.
