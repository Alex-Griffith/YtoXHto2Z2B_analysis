"""Run-3 H->ZZ(*)->4l selection ported from lwang046/H4LTools.

The first port intentionally uses the no-FSR four-vectors, matching the
reference configuration's isFSR=False output. FSR association is kept as the
next isolated validation item rather than mixed into the jet/Y work.
"""

import itertools

from .kinematics import add, delta_r


def _electron(tree, i):
    return {"kind": "e", "index": i, "pt": float(tree.Electron_pt[i]),
            "eta": float(tree.Electron_eta[i]), "phi": float(tree.Electron_phi[i]),
            "mass": float(tree.Electron_mass[i]), "charge": int(tree.Electron_charge[i])}


def _muon(tree, i):
    return {"kind": "mu", "index": i, "pt": float(tree.Muon_pt[i]),
            "eta": float(tree.Muon_eta[i]), "phi": float(tree.Muon_phi[i]),
            "mass": float(tree.Muon_mass[i]), "charge": int(tree.Muon_charge[i])}


def select_leptons(tree, objects, cuts):
    electrons, muons = [], []
    for i in range(int(tree.nElectron)):
        loose = (float(tree.Electron_pt[i]) > objects["electron_pt_min"] and
                 abs(float(tree.Electron_eta[i])) < objects["electron_eta_max"] and
                 abs(float(tree.Electron_sip3d[i])) < 4.0 and
                 abs(float(tree.Electron_dxy[i])) < 0.5 and
                 abs(float(tree.Electron_dz[i])) < 1.0)
        if loose and bool(tree.Electron_mvaIso_WPHZZ[i]):
            electrons.append(_electron(tree, i))

    for i in range(int(tree.nMuon)):
        loose = (float(tree.Muon_pt[i]) > objects["muon_pt_min"] and
                 abs(float(tree.Muon_eta[i])) < objects["muon_eta_max"] and
                 (bool(tree.Muon_isGlobal[i]) or bool(tree.Muon_isTracker[i])) and
                 abs(float(tree.Muon_sip3d[i])) < 4.0 and
                 abs(float(tree.Muon_dxy[i])) < 0.5 and
                 abs(float(tree.Muon_dz[i])) < 1.0)
        tight_id = (bool(tree.Muon_looseId[i]) and
                    float(tree.Muon_mvaLowPt[i]) > cuts["muon_mva_low_pt_min"])
        isolated = float(tree.Muon_pfRelIso03_all[i]) < cuts["muon_iso_max"]
        if loose and tight_id and isolated:
            muons.append(_muon(tree, i))
    return electrons, muons


def _z_candidates(leptons, cuts):
    candidates = []
    for first, second in itertools.combinations(leptons, 2):
        if first["kind"] != second["kind"] or first["charge"] + second["charge"] != 0:
            continue
        vector = add(first, second)
        if cuts["z_mass_min"] < vector["mass"] < cuts["z_mass_max"]:
            candidates.append({"l1": first, "l2": second, "p4": vector})
    return candidates


def _passes_smart_cut(four, chosen_z1, cuts):
    """Reference 4e/4mu alternate-pairing suppression."""
    if len({lepton["kind"] for lepton in four}) != 1:
        return True
    alternatives = _z_candidates(four, cuts)
    for za, zb in itertools.combinations(alternatives, 2):
        ids_a = {(za["l1"]["kind"], za["l1"]["index"]), (za["l2"]["kind"], za["l2"]["index"])}
        ids_b = {(zb["l1"]["kind"], zb["l1"]["index"]), (zb["l2"]["kind"], zb["l2"]["index"])}
        if ids_a & ids_b or len(ids_a | ids_b) != 4:
            continue
        alt_z1, alt_z2 = sorted((za, zb), key=lambda z: abs(z["p4"]["mass"] - cuts["z_mass"]))
        if (abs(alt_z1["p4"]["mass"] - cuts["z_mass"]) <
                abs(chosen_z1["p4"]["mass"] - cuts["z_mass"]) and
                alt_z2["p4"]["mass"] < cuts["z_mass_min"]):
            return False
    return True


def select_hzz4l(tree, objects, cuts):
    electrons, muons = select_leptons(tree, objects, cuts)
    leptons = electrons + muons
    result = {"n_tight_electrons": len(electrons), "n_tight_muons": len(muons),
              "tight_leptons": leptons, "pass_four_leptons": len(leptons) >= 4,
              "pass_z_candidates": False, "pass_ghost": False, "pass_lepton_pt": False,
              "pass_qcd": False, "pass_zz": False, "pass_h_window": False,
              "candidate": None}
    if len(leptons) < 4:
        return result

    zs = _z_candidates(leptons, cuts)
    result["pass_z_candidates"] = len(zs) >= 2
    valid = []
    for za, zb in itertools.combinations(zs, 2):
        ids_a = {(za["l1"]["kind"], za["l1"]["index"]), (za["l2"]["kind"], za["l2"]["index"])}
        ids_b = {(zb["l1"]["kind"], zb["l1"]["index"]), (zb["l2"]["kind"], zb["l2"]["index"])}
        if ids_a & ids_b:
            continue
        four = [za["l1"], za["l2"], zb["l1"], zb["l2"]]
        if any(delta_r(a, b) <= 0.02 for a, b in itertools.combinations(four, 2)):
            continue
        result["pass_ghost"] = True
        pts = sorted((x["pt"] for x in four), reverse=True)
        if pts[0] <= cuts["leading_lepton_pt_min"] or pts[1] <= cuts["subleading_lepton_pt_min"]:
            continue
        result["pass_lepton_pt"] = True
        qcd_ok = True
        for a, b in itertools.combinations(four, 2):
            if a["charge"] + b["charge"] == 0 and add(a, b)["mass"] < cuts["opposite_sign_pair_mass_min"]:
                qcd_ok = False; break
        if not qcd_ok:
            continue
        result["pass_qcd"] = True
        z1, z2 = sorted((za, zb), key=lambda z: abs(z["p4"]["mass"] - cuts["z_mass"]))
        if z1["p4"]["mass"] <= cuts["z1_mass_min"]:
            continue
        if not _passes_smart_cut(four, z1, cuts):
            continue
        four_vector = add(*four)
        if z1["p4"]["mass"] + z2["p4"]["mass"] < cuts["zz_mass_min"]:
            continue
        valid.append((abs(z1["p4"]["mass"] - cuts["z_mass"]),
                      -(z2["l1"]["pt"] + z2["l2"]["pt"]), z1, z2, four_vector, four))
    if not valid:
        return result
    _, _, z1, z2, four_vector, four = min(valid, key=lambda x: (x[0], x[1]))
    result["pass_zz"] = True
    result["pass_h_window"] = cuts["h_mass_min"] < four_vector["mass"] < cuts["h_mass_max"]
    ordered_leptons = [z1["l1"], z1["l2"], z2["l1"], z2["l2"]]
    result["candidate"] = {
        "z1_mass": z1["p4"]["mass"], "z2_mass": z2["p4"]["mass"],
        "z1": z1["p4"], "z2": z2["p4"],
        "mass4l": four_vector["mass"], "pt4l": four_vector["pt"],
        "pt": four_vector["pt"], "eta": four_vector["eta"],
        "phi": four_vector["phi"], "mass": four_vector["mass"],
        "rapidity": four_vector["rapidity"],
        "leptons": ordered_leptons,
    }
    return result
