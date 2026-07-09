"""Minimal, deliberately transparent NanoAOD event processor."""

import json
from collections import Counter
from pathlib import Path

from .hzz4l import select_hzz4l
from .jets import JetSelector
from .truth import classify_signal


def _as_list(value):
    return [value[i] for i in range(len(value))]


def _branch_names(tree):
    return {branch.GetName() for branch in tree.GetListOfBranches()}


def run(input_path, config_path, output_path, max_events=-1):
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
        if trigger_pass and hzz["pass_zz"] and jets["pass_two_jets"]:
            counts["selected_trigger_hzz4l_resolved2j"] += 1

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

    result = {
        "input": str(input_path),
        "is_mc": is_mc,
        "entries_processed": stop,
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
    root_file.Close()
    return result
