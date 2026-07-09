"""Minimal, deliberately transparent NanoAOD event processor."""

import json
from collections import Counter
from pathlib import Path

from .hzz4l import select_hzz4l
from .jets import JetSelector
from .kinematics import add, delta_r
from .ntuple import PlotNtuple
from .truth import classify_signal


def _as_list(value):
    return [value[i] for i in range(len(value))]


def _branch_names(tree):
    return {branch.GetName() for branch in tree.GetListOfBranches()}


def _fill_object(row, prefix, obj):
    if obj is None:
        return
    row[f"pT{prefix}"] = obj["pt"]
    row[f"eta{prefix}"] = obj["eta"]
    row[f"phi{prefix}"] = obj["phi"]
    row[f"mass{prefix}" if prefix.startswith("L") else f"m{prefix}"] = obj["mass"]


def run(input_path, config_path, output_path, max_events=-1, root_output_path=None):
    import ROOT

    config = json.loads(Path(config_path).read_text())
    signal = config["signal"]
    objects = config["objects"]

    root_file = ROOT.TFile.Open(str(input_path))
    if not root_file or root_file.IsZombie():
        raise RuntimeError(f"Cannot open NanoAOD file: {input_path}")
    tree = root_file.Get("Events")
    if not tree:
        raise RuntimeError("Input does not contain an Events tree")

    branches = _branch_names(tree)
    trigger_names = [name for name in config["triggers"] if name in branches]
    is_mc = {"nGenPart", "GenPart_pdgId", "GenPart_genPartIdxMother"}.issubset(branches)
    jet_selector = JetSelector(objects, config["jets"])
    if root_output_path is None:
        root_output_path = str(Path(output_path).with_suffix(".root"))
    ntuple = PlotNtuple(root_output_path, ROOT)

    counts = Counter()
    decay_modes = Counter()
    selected_m4l = []
    selected_mbb = []
    n_entries = int(tree.GetEntries())
    stop = n_entries if max_events < 0 else min(n_entries, max_events)

    for entry in range(stop):
        tree.GetEntry(entry)
        counts["all"] += 1

        trigger_pass = any(bool(getattr(tree, name)) for name in trigger_names)
        if trigger_pass:
            counts["trigger"] += 1

        hzz = select_hzz4l(tree, objects, config["hzz4l"])
        for key in ("pass_four_leptons", "pass_z_candidates", "pass_ghost",
                    "pass_lepton_pt", "pass_qcd", "pass_zz", "pass_h_window"):
            if hzz[key]:
                counts[f"hzz4l_{key}"] += 1

        jets = jet_selector.select(tree, hzz["tight_leptons"])
        if jets["pass_two_jets"]:
            counts["resolved_two_clean_jets"] += 1
            selected_mbb.append(jets["candidate"]["mass"])
        if hzz["pass_zz"]:
            selected_m4l.append(hzz["candidate"]["mass4l"])
        pass_baseline = trigger_pass and hzz["pass_zz"] and jets["pass_two_jets"]
        pass_signal_region = pass_baseline and hzz["pass_h_window"]
        if pass_baseline:
            counts["selected_trigger_hzz4l_resolved2j"] += 1
        if pass_signal_region:
            counts["selected_signal_region"] += 1

        truth = {}
        if is_mc:
            truth = classify_signal(
                _as_list(tree.GenPart_pdgId),
                _as_list(tree.GenPart_status),
                _as_list(tree.GenPart_genPartIdxMother),
                x_pdg=signal["x_pdg_id"],
                y_pdg=signal["y_pdg_id"],
                h_pdg=signal["h_pdg_id"],
            )
            for key in ("has_xyh", "has_ybb", "has_h4l", "valid_signal"):
                if truth[key]:
                    counts[f"truth_{key}"] += 1
            if truth["valid_signal"]:
                decay_modes[f"{hzz['n_tight_electrons']}e{hzz['n_tight_muons']}mu_tight"] += 1

        row = {
            "run": getattr(tree, "run", 0),
            "luminosityBlock": getattr(tree, "luminosityBlock", 0),
            "event": getattr(tree, "event", entry),
            "isMC": is_mc,
            "genWeight": getattr(tree, "genWeight", 1.0),
            "pileup_nTrueInt": getattr(tree, "Pileup_nTrueInt", -99.0),
            "nElectron": tree.nElectron, "nMuon": tree.nMuon, "nJet": tree.nJet,
            "nTightEle": hzz["n_tight_electrons"],
            "nTightMu": hzz["n_tight_muons"],
            "nSelectedJet": len(jets["jets"]),
            "passedTrig": trigger_pass,
            "passedFourLeptons": hzz["pass_four_leptons"],
            "passedZCandidates": hzz["pass_z_candidates"],
            "passedGhost": hzz["pass_ghost"],
            "passedLeptonPt": hzz["pass_lepton_pt"],
            "passedQCD": hzz["pass_qcd"],
            "passedZZ": hzz["pass_zz"],
            "passedHWindow": hzz["pass_h_window"],
            "passedTwoJets": jets["pass_two_jets"],
            "passedBaseline": pass_baseline,
            "passedSignalRegion": pass_signal_region,
            "truthHasXYH": truth.get("has_xyh", False),
            "truthHasYbb": truth.get("has_ybb", False),
            "truthHasH4l": truth.get("has_h4l", False),
            "truthValidSignal": truth.get("valid_signal", False),
            "pv_npvs": getattr(tree, "PV_npvs", -1),
            "pv_npvsGood": getattr(tree, "PV_npvsGood", -1),
            "fixedGridRhoFastjetAll": getattr(tree, "fixedGridRhoFastjetAll", -99.0),
            "met": getattr(tree, "PuppiMET_pt", getattr(tree, "MET_pt", -99.0)),
            "metPhi": getattr(tree, "PuppiMET_phi", getattr(tree, "MET_phi", -99.0)),
            "mXHypothesis": signal["m_x"], "mYHypothesis": signal["m_y"],
        }
        if hzz["pass_zz"]:
            candidate = hzz["candidate"]
            row.update({
                "mass4l": candidate["mass"], "pT4l": candidate["pt"],
                "eta4l": candidate["eta"], "phi4l": candidate["phi"],
                "rapidity4l": candidate["rapidity"],
                "massZ1": candidate["z1"]["mass"], "pTZ1": candidate["z1"]["pt"],
                "etaZ1": candidate["z1"]["eta"], "phiZ1": candidate["z1"]["phi"],
                "massZ2": candidate["z2"]["mass"], "pTZ2": candidate["z2"]["pt"],
                "etaZ2": candidate["z2"]["eta"], "phiZ2": candidate["z2"]["phi"],
            })
            n_electrons = sum(lepton["kind"] == "e" for lepton in candidate["leptons"])
            row["finalState"] = {0: 1, 4: 2, 2: 3}.get(n_electrons, -1)
            row[{0: "mass4mu", 4: "mass4e", 2: "mass2e2mu"}[n_electrons]] = candidate["mass"]
            for index, lepton in enumerate(candidate["leptons"], 1):
                _fill_object(row, f"L{index}", lepton)
                row[f"chargeL{index}"] = lepton["charge"]
                row[f"pdgIdL{index}"] = (-11 if lepton["kind"] == "e" else -13) * lepton["charge"]
        if jets["pass_two_jets"]:
            dijet = jets["candidate"]
            _fill_object(row, "j1", dijet["jet1"])
            _fill_object(row, "j2", dijet["jet2"])
            row["btagj1"] = dijet["jet1"]["btag"]
            row["btagj2"] = dijet["jet2"]["btag"]
            row.update({
                "massbb": dijet["mass"], "pTbb": dijet["pt"],
                "etabb": dijet["eta"], "phibb": dijet["phi"],
                "rapiditybb": dijet["rapidity"],
                "deltaRbb": delta_r(dijet["jet1"], dijet["jet2"]),
                "jetHT": sum(jet["pt"] for jet in jets["jets"]),
            })
        if hzz["pass_zz"] and jets["pass_two_jets"]:
            resonance = add(hzz["candidate"], jets["candidate"])
            row.update({
                "massbb4l": resonance["mass"], "pTbb4l": resonance["pt"],
                "etabb4l": resonance["eta"], "phibb4l": resonance["phi"],
                "rapiditybb4l": resonance["rapidity"],
                "deltaRbb4l": delta_r(hzz["candidate"], jets["candidate"]),
            })
        ntuple.fill(row)

    result = {
        "input": str(input_path),
        "is_mc": is_mc,
        "entries_processed": stop,
        "plot_ntuple": str(root_output_path),
        "available_triggers": trigger_names,
        "selection_status": {
            "hzz4l": "reference-compatible no-FSR port; MELA discriminants not evaluated",
            "jets": "official NanoAODv15 AK4PUPPI Tight JetID recomputed; UParT ranking"
        },
        "schema": {
            "input_has_jet_id": "Jet_jetId" in branches,
            "jet_id_recomputed": True,
            "btag_branch": config["jets"]["tagger"],
            "warnings": ["Input Jet_jetId is absent; official v15 JetID is recomputed from jet constituents."]
        },
        "cutflow": dict(counts),
        "selected_observables": {"mass4l": selected_m4l, "mass_bb": selected_mbb},
        "reco_flavor_counts_for_valid_signal": dict(decay_modes),
        "config": config,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    ntuple.close(result["cutflow"])
    root_file.Close()
    return result
