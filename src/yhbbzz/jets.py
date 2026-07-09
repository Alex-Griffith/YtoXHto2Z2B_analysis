"""NanoAODv15 AK4 PUPPI jet selection and UParT Y->bb candidate."""

from .kinematics import add, delta_r


class JetSelector:
    def __init__(self, objects, config):
        import correctionlib
        self.objects = objects
        self.config = config
        cset = correctionlib.CorrectionSet.from_file(config["jet_id_json"])
        self.jet_id = cset[config["jet_id_key"]]

    def _pass_jet_id(self, tree, i):
        multiplicity = int(tree.Jet_chMultiplicity[i]) + int(tree.Jet_neMultiplicity[i])
        return bool(self.jet_id.evaluate(
            float(tree.Jet_eta[i]), float(tree.Jet_chHEF[i]), float(tree.Jet_neHEF[i]),
            float(tree.Jet_chEmEF[i]), float(tree.Jet_neEmEF[i]), float(tree.Jet_muEF[i]),
            int(tree.Jet_chMultiplicity[i]), int(tree.Jet_neMultiplicity[i]), multiplicity))

    def select(self, tree, tight_leptons):
        tagger = self.config["tagger"]
        selected = []
        for i in range(int(tree.nJet)):
            jet = {"index": i, "pt": float(tree.Jet_pt[i]), "eta": float(tree.Jet_eta[i]),
                   "phi": float(tree.Jet_phi[i]), "mass": float(tree.Jet_mass[i]),
                   "btag": float(getattr(tree, tagger)[i])}
            if jet["pt"] <= self.objects["jet_pt_min"] or abs(jet["eta"]) >= self.objects["jet_eta_max"]:
                continue
            if not self._pass_jet_id(tree, i):
                continue
            if any(delta_r(jet, lepton) < self.config["cleaning_dr"] for lepton in tight_leptons):
                continue
            selected.append(jet)
        selected.sort(key=lambda jet: jet["btag"], reverse=True)
        candidate = None
        if len(selected) >= 2:
            dijet = add(selected[0], selected[1])
            candidate = {"jet1": selected[0], "jet2": selected[1],
                         "mass": dijet["mass"], "pt": dijet["pt"]}
        return {"jets": selected, "candidate": candidate, "pass_two_jets": candidate is not None}

