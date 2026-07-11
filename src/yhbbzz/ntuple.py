"""Small plotting ntuple inspired by the non-resonant H4L skim."""

import json
from array import array
from pathlib import Path


FLOAT_BRANCHES = (
    "genWeight", "baseEventWeight", "normalizedWeight", "pileup_nTrueInt",
    "mass4l", "mass4e", "mass4mu", "mass2e2mu",
    "pT4l", "eta4l", "phi4l", "rapidity4l",
    "massZ1", "pTZ1", "etaZ1", "phiZ1",
    "massZ2", "pTZ2", "etaZ2", "phiZ2",
    "pTL1", "etaL1", "phiL1", "massL1",
    "pTL2", "etaL2", "phiL2", "massL2",
    "pTL3", "etaL3", "phiL3", "massL3",
    "pTL4", "etaL4", "phiL4", "massL4",
    "pTj1", "etaj1", "phij1", "mj1", "btagj1",
    "pTj2", "etaj2", "phij2", "mj2", "btagj2",
    "massbb", "pTbb", "etabb", "phibb", "rapiditybb", "deltaRbb",
    "massbb4l", "pTbb4l", "etabb4l", "phibb4l", "rapiditybb4l", "deltaRbb4l",
    "jetHT", "met", "metPhi", "fixedGridRhoFastjetAll",
    "mXHypothesis", "mYHypothesis",
)

INT_BRANCHES = (
    "nElectron", "nMuon", "nJet", "nTightEle", "nTightMu",
    "nSelectedJet", "finalState", "pdgIdL1", "pdgIdL2", "pdgIdL3", "pdgIdL4",
    "chargeL1", "chargeL2", "chargeL3", "chargeL4",
    "pv_npvs", "pv_npvsGood",
)

BOOL_BRANCHES = (
    "isMC", "passedTrig", "passedFourLeptons", "passedZCandidates",
    "passedGhost", "passedLeptonPt", "passedQCD", "passedZZ",
    "passedHWindow", "passedTwoJets", "passedBaseline",
    "passedSignalRegion", "truthHasXYH", "truthHasYbb", "truthHasH4l",
    "truthValidSignal",
)


class PlotNtuple:
    """Write one compact row per processed input event."""

    def __init__(self, path, root):
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.path = output
        self.root = root
        self.file = root.TFile.Open(str(output), "RECREATE")
        if not self.file or self.file.IsZombie():
            raise RuntimeError(f"Cannot create plotting ROOT file: {output}")
        self.tree = root.TTree("Events", "YH(bb,4l) plotting ntuple")
        self.values = {}
        for name in ("run", "luminosityBlock"):
            self._branch(name, "I", "i")
        self._branch("event", "L", "l")
        for name in INT_BRANCHES:
            self._branch(name, "i", "I")
        for name in BOOL_BRANCHES:
            self._branch(name, "b", "O")
        for name in FLOAT_BRANCHES:
            self._branch(name, "f", "F")

    def _branch(self, name, array_code, leaf_code):
        value = array(array_code, [0])
        self.values[name] = value
        self.tree.Branch(name, value, f"{name}/{leaf_code}")

    def fill(self, row):
        for name in INT_BRANCHES:
            value = row.get(name, -1)
            # PyROOT exposes NanoAOD UChar_t leaves as one-character strings.
            if isinstance(value, str) and len(value) == 1:
                value = ord(value)
            self.values[name][0] = int(value)
        for name in BOOL_BRANCHES:
            self.values[name][0] = bool(row.get(name, False))
        for name in FLOAT_BRANCHES:
            self.values[name][0] = float(row.get(name, -99.0))
        self.values["run"][0] = int(row.get("run", 0))
        self.values["luminosityBlock"][0] = int(row.get("luminosityBlock", 0))
        self.values["event"][0] = int(row.get("event", 0))
        self.tree.Fill()

    def _write_cutflow(self, name, title, cutflow):
        histogram = self.root.TH1D(name, title, len(cutflow), 0, len(cutflow))
        for index, (label, count) in enumerate(cutflow.items(), 1):
            histogram.GetXaxis().SetBinLabel(index, label)
            histogram.SetBinContent(index, count)
        histogram.Write()

    def close(self, cutflow=None, sequential_cutflow=None, metadata=None):
        self.file.cd()
        self.tree.Write()
        if cutflow:
            self._write_cutflow("Cutflow", "Event cutflow", cutflow)
        if sequential_cutflow:
            self._write_cutflow(
                "SequentialCutflow", "Sequential event cutflow", sequential_cutflow
            )
        if metadata is not None:
            self.root.TObjString(json.dumps(metadata, sort_keys=True)).Write("SampleMetadata")
        self.file.Close()
