# Reference implementation map

Physics reference: `lwang046/HHbbZZ`, branch `HHbbZZ_Analysis_Run3`, commit
`0bd83e6aec9e15179bb54b724dffc7689eee32fa`.

| New module | Reference responsibility |
|---|---|
| `hzz4l.py` | `H4LTools.cc`: Run-3 electron/muon selection, OS-SF Z candidates, ghost removal, 20/10 GeV requirements, low-mass OS-pair rejection, smart cut and best Z1/Z2 choice |
| `jets.py` | `H4LTools::SelectedJets`, `BuildBestDijet`, plus `NATModules.jetId` |
| `truth.py` | New topology-specific ancestry for `45 -> 35 + 25`, `35 -> bb`, `25 -> ZZ -> 4l` |

Intentional boundaries:

- The current reconstructed selection uses no-FSR four-vectors.  FSR recovery
  will be validated separately against the reference before being enabled.
- MELA discriminants do not decide event acceptance and are not yet evaluated.
- No `m_bb` window is applied; it must remain mass-point configurable.
- 2024 NanoAODv15 jets use official recomputed AK4PUPPI Tight JetID and
  `Jet_btagUParTAK4B` ordering.
