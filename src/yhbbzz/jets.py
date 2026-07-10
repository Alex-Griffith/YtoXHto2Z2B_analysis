"""AK4 PUPPI jet selection and b-tag-ranked Y->bb candidate."""

from .kinematics import add, delta_r


class JetSelector:
    def __init__(self, objects, config, branches):
        self.objects = objects
        self.config = config
        self.branches = branches
        self.warnings = []
        self.tagger = self._resolve_tagger()
        self.use_input_jet_id = "Jet_jetId" in branches
        self.jet_id_recomputed = not self.use_input_jet_id
        self.jet_id = None
        if self.jet_id_recomputed:
            import correctionlib
            cset = correctionlib.CorrectionSet.from_file(config["jet_id_json"])
            self.jet_id = cset[config["jet_id_key"]]
            self.warnings.append("Input Jet_jetId is absent; official JetID is recomputed from jet constituents.")

    def _resolve_tagger(self):
        requested = self.config.get("tagger", "Jet_btagUParTAK4B")
        fallbacks = self.config.get("tagger_fallbacks", [
            "Jet_btagUParTAK4B", "Jet_btagPNetB", "Jet_btagDeepFlavB"
        ])
        candidates = []
        for name in [requested, *fallbacks]:
            if name not in candidates:
                candidates.append(name)
        for name in candidates:
            if name in self.branches:
                if name != requested:
                    self.warnings.append(f"Configured b tagger {requested} is absent; using {name}.")
                return name
        raise RuntimeError(f"No supported AK4 b tagger branch found. Tried: {', '.join(candidates)}")

    def _pass_jet_id(self, tree, i):
        if self.use_input_jet_id:
            return int(tree.Jet_jetId[i]) >= int(self.objects.get("jet_id_min", 1))
        multiplicity = int(tree.Jet_chMultiplicity[i]) + int(tree.Jet_neMultiplicity[i])
        return bool(self.jet_id.evaluate(
            float(tree.Jet_eta[i]), float(tree.Jet_chHEF[i]), float(tree.Jet_neHEF[i]),
            float(tree.Jet_chEmEF[i]), float(tree.Jet_neEmEF[i]), float(tree.Jet_muEF[i]),
            int(tree.Jet_chMultiplicity[i]), int(tree.Jet_neMultiplicity[i]), multiplicity))

    def select(self, tree, tight_leptons):
        selected = []
        for i in range(int(tree.nJet)):
            jet = {"index": i, "pt": float(tree.Jet_pt[i]), "eta": float(tree.Jet_eta[i]),
                   "phi": float(tree.Jet_phi[i]), "mass": float(tree.Jet_mass[i]),
                   "btag": float(getattr(tree, self.tagger)[i])}
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
                         "mass": dijet["mass"], "pt": dijet["pt"],
                         "eta": dijet["eta"], "phi": dijet["phi"],
                         "rapidity": dijet["rapidity"]}
        return {"jets": selected, "candidate": candidate, "pass_two_jets": candidate is not None}
