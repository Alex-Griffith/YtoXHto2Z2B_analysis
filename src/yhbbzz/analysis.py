"""Minimal, deliberately transparent NanoAOD event processor."""

import json
from collections import Counter
from pathlib import Path

from .hzz4l import resolve_electron_hzz_id, select_hzz4l
from .jets import JetSelector
from .kinematics import add, delta_r
from .ntuple import PlotNtuple
from .truth import classify_signal


SEQUENTIAL_STAGES = (
    "all", "trigger", "four_leptons", "z_candidates", "ghost_removal",
    "lepton_pt", "low_mass_pair_rejection", "hzz4l_candidate",
    "two_clean_jets", "higgs_mass_window",
)


def _as_list(value):
    return [value[i] for i in range(len(value))]


def _branch_names(tree):
    return {branch.GetName() for branch in tree.GetListOfBranches()}


def _normalize_input_path(path):
    path = str(path).strip()
    if path.startswith("/store/"):
        return f"root://cms-xrd-global.cern.ch/{path}"
    return path


def _input_files(input_path):
    input_path = str(input_path)
    if input_path.endswith(".txt") and not input_path.startswith("root://"):
        files = []
        for line in Path(input_path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            files.append(_normalize_input_path(line))
        if not files:
            raise RuntimeError(f"Input file list is empty: {input_path}")
        return files
    return [_normalize_input_path(input_path)]


def _fill_object(row, prefix, obj):
    if obj is None:
        return
    row[f"pT{prefix}"] = obj["pt"]
    row[f"eta{prefix}"] = obj["eta"]
    row[f"phi{prefix}"] = obj["phi"]
    row[f"mass{prefix}" if prefix.startswith("L") else f"m{prefix}"] = obj["mass"]


def _resolve_sample_type(config, branches, requested):
    sample_type = (requested or config.get("sample_type", "auto")).lower()
    if sample_type not in {"auto", "data", "mc"}:
        raise ValueError("sample_type must be one of: auto, data, mc")
    has_gen = {"nGenPart", "GenPart_pdgId", "GenPart_genPartIdxMother"}.issubset(branches)
    if sample_type == "auto":
        return "mc" if has_gen else "data"
    return sample_type


def _resolve_nanoaod_version(config, requested):
    version = (requested or config.get("nanoaod_version", "auto")).lower()
    if version not in {"auto", "v12", "v15"}:
        raise ValueError("nanoaod_version must be one of: auto, v12, v15")
    return version


def _infer_nanoaod_version(branches):
    if "Jet_btagUParTAK4B" in branches:
        return "v15-like"
    if "Jet_btagPNetB" in branches:
        return "v12-like"
    return "unknown"


def _normalization_info(is_mc, metadata):
    """Resolve an optional luminosity normalization without inventing inputs."""
    info = {
        "status": "data_unit_weight" if not is_mc else "missing_metadata",
        "formula": "genWeight * cross_section_pb * luminosity_fb * 1000 / sum_gen_weight",
        "scale_per_gen_weight": 1.0 if not is_mc else None,
        "missing_fields": [],
    }
    if not is_mc:
        return info

    required = ("cross_section_pb", "luminosity_fb", "sum_gen_weight")
    missing = [name for name in required if metadata.get(name) is None]
    info["missing_fields"] = missing
    if missing:
        return info

    cross_section_pb = float(metadata["cross_section_pb"])
    luminosity_fb = float(metadata["luminosity_fb"])
    sum_gen_weight = float(metadata["sum_gen_weight"])
    if sum_gen_weight == 0.0:
        info["status"] = "invalid_zero_sum_gen_weight"
        return info
    info["status"] = "base_normalization_available"
    info["scale_per_gen_weight"] = cross_section_pb * luminosity_fb * 1000.0 / sum_gen_weight
    return info


def run(input_path, config_path, output_path, max_events=-1, root_output_path=None,
        sample_type=None, nanoaod_version=None, sample_metadata=None):
    import ROOT

    config = json.loads(Path(config_path).read_text())
    signal = config["signal"]
    objects = config["objects"]

    input_files = _input_files(input_path)
    tree = ROOT.TChain("Events")
    for path in input_files:
        if tree.Add(path) == 0:
            raise RuntimeError(f"Cannot add NanoAOD file to Events chain: {path}")

    branches = _branch_names(tree)
    if not branches:
        raise RuntimeError("Input does not contain an Events tree with branches")
    requested_nanoaod_version = _resolve_nanoaod_version(config, nanoaod_version)
    resolved_sample_type = _resolve_sample_type(config, branches, sample_type)
    is_mc = resolved_sample_type == "mc"
    resolved_metadata = dict(config.get("sample_metadata", {}))
    resolved_metadata.update(sample_metadata or {})
    resolved_metadata.update({
        "sample_type": resolved_sample_type,
        "nanoaod_version_requested": requested_nanoaod_version,
    })
    normalization = _normalization_info(is_mc, resolved_metadata)
    truth_branches = {"nGenPart", "GenPart_pdgId", "GenPart_status", "GenPart_genPartIdxMother"}
    truth_enabled = is_mc and truth_branches.issubset(branches)
    trigger_names = [name for name in config["triggers"] if name in branches]
    missing_triggers = [name for name in config["triggers"] if name not in branches]
    warnings = []
    if missing_triggers:
        warnings.append(f"Missing HLT branches skipped: {', '.join(missing_triggers)}")
    if is_mc and not truth_enabled:
        warnings.append("MC sample requested but truth GenPart branches are incomplete; truth matching skipped.")
    electron_hzz_id = resolve_electron_hzz_id(branches)
    if electron_hzz_id is None:
        warnings.append("No supported HZZ electron ID branch found; electrons will fail HZZ ID.")

    jet_selector = JetSelector(objects, config["jets"], branches)
    warnings.extend(jet_selector.warnings)
    if root_output_path is None:
        root_output_path = str(Path(output_path).with_suffix(".root"))
    ntuple = PlotNtuple(root_output_path, ROOT)

    counts = Counter()
    sequential_counts = Counter({stage: 0 for stage in SEQUENTIAL_STAGES})
    sequential_sum_gen_weight = Counter({stage: 0.0 for stage in SEQUENTIAL_STAGES})
    sequential_sum_gen_weight2 = Counter({stage: 0.0 for stage in SEQUENTIAL_STAGES})
    decay_modes = Counter()
    selected_m4l = []
    selected_mbb = []
    n_entries = int(tree.GetEntries())
    stop = n_entries if max_events < 0 else min(n_entries, max_events)

    for entry in range(stop):
        tree.GetEntry(entry)
        counts["all"] += 1
        event_gen_weight = (
            float(getattr(tree, "genWeight", 1.0))
            if is_mc and "genWeight" in branches else 1.0
        )

        trigger_pass = any(bool(getattr(tree, name)) for name in trigger_names)
        if trigger_pass:
            counts["trigger"] += 1

        hzz = select_hzz4l(tree, objects, config["hzz4l"], electron_hzz_id)
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

        sequential_flags = {
            "all": True,
            "trigger": trigger_pass,
            "four_leptons": trigger_pass and hzz["pass_four_leptons"],
            "z_candidates": trigger_pass and hzz["pass_z_candidates"],
            "ghost_removal": trigger_pass and hzz["pass_ghost"],
            "lepton_pt": trigger_pass and hzz["pass_lepton_pt"],
            "low_mass_pair_rejection": trigger_pass and hzz["pass_qcd"],
            "hzz4l_candidate": trigger_pass and hzz["pass_zz"],
            "two_clean_jets": pass_baseline,
            "higgs_mass_window": pass_signal_region,
        }
        for stage, passed in sequential_flags.items():
            if passed:
                sequential_counts[stage] += 1
                sequential_sum_gen_weight[stage] += event_gen_weight
                sequential_sum_gen_weight2[stage] += event_gen_weight * event_gen_weight

        truth = {}
        if truth_enabled:
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
            "genWeight": event_gen_weight,
            "baseEventWeight": event_gen_weight,
            "normalizedWeight": (
                event_gen_weight * normalization["scale_per_gen_weight"]
                if normalization["scale_per_gen_weight"] is not None else -99.0
            ),
            "pileup_nTrueInt": getattr(tree, "Pileup_nTrueInt", -99.0) if is_mc and "Pileup_nTrueInt" in branches else -99.0,
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

    normalized_cutflow = {}
    if normalization["scale_per_gen_weight"] is not None:
        normalized_cutflow = {
            stage: value * normalization["scale_per_gen_weight"]
            for stage, value in sequential_sum_gen_weight.items()
        }

    result = {
        "input": str(input_path),
        "inputs": input_files,
        "is_mc": is_mc,
        "sample_type": resolved_sample_type,
        "nanoaod_version": {
            "requested": requested_nanoaod_version,
            "inferred": _infer_nanoaod_version(branches),
        },
        "entries_processed": stop,
        "plot_ntuple": str(root_output_path),
        "available_triggers": trigger_names,
        "missing_triggers": missing_triggers,
        "selection_status": {
            "hzz4l": "reference-compatible no-FSR port; MELA discriminants not evaluated",
            "jets": "AK4PUPPI JetID from NanoAOD when available, otherwise recomputed; b-tag ranking uses branch fallback"
        },
        "schema": {
            "input_has_jet_id": "Jet_jetId" in branches,
            "jet_id_recomputed": jet_selector.jet_id_recomputed,
            "btag_branch": jet_selector.tagger,
            "electron_hzz_id": electron_hzz_id,
            "truth_matching_enabled": truth_enabled,
            "warnings": warnings,
        },
        "cutflow": dict(counts),
        "sequential_cutflow": dict(sequential_counts),
        "sequential_sum_gen_weight": dict(sequential_sum_gen_weight),
        "sequential_sum_gen_weight2": dict(sequential_sum_gen_weight2),
        "normalized_sequential_cutflow": normalized_cutflow,
        "sample_metadata": resolved_metadata,
        "normalization": normalization,
        "selected_observables": {"mass4l": selected_m4l, "mass_bb": selected_mbb},
        "reco_flavor_counts_for_valid_signal": dict(decay_modes),
        "config": config,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    ntuple.close(
        result["cutflow"],
        sequential_cutflow=result["sequential_cutflow"],
        metadata={
            "sample_metadata": result["sample_metadata"],
            "normalization": result["normalization"],
        },
    )
    return result
