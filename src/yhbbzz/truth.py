"""Generator-level ancestry helpers independent of ROOT and CMSSW."""


def ancestors(index, mothers):
    """Yield valid mother indices, stopping safely on malformed ancestry."""
    seen = set()
    current = index
    while 0 <= current < len(mothers):
        mother = int(mothers[current])
        if mother < 0 or mother >= len(mothers) or mother in seen:
            return
        seen.add(mother)
        yield mother
        current = mother


def has_ancestor(index, ancestor_pdg_id, pdg_ids, mothers):
    target = abs(int(ancestor_pdg_id))
    return any(abs(int(pdg_ids[i])) == target for i in ancestors(index, mothers))


def direct_decay(parent_pdg_id, daughter_pdg_ids, pdg_ids, mothers):
    """Return true if one parent has the requested direct daughters."""
    target_parent = abs(int(parent_pdg_id))
    requested = sorted(abs(int(x)) for x in daughter_pdg_ids)
    for parent, pdg_id in enumerate(pdg_ids):
        if abs(int(pdg_id)) != target_parent:
            continue
        found = sorted(
            abs(int(pdg_ids[i]))
            for i, mother in enumerate(mothers)
            if int(mother) == parent
        )
        if all(found.count(pdg) >= requested.count(pdg) for pdg in set(requested)):
            return True
    return False


def classify_signal(pdg_ids, status, mothers, x_pdg=45, y_pdg=35, h_pdg=25):
    """Classify the X->YH, Y->bb, H->ZZ->4l generator topology."""
    has_xyh = direct_decay(x_pdg, [y_pdg, h_pdg], pdg_ids, mothers)
    has_ybb = direct_decay(y_pdg, [5, 5], pdg_ids, mothers)

    h_leptons = []
    y_b_quarks = []
    for i, pdg_id in enumerate(pdg_ids):
        abs_id = abs(int(pdg_id))
        if abs_id in (11, 13) and int(status[i]) == 1:
            if has_ancestor(i, 23, pdg_ids, mothers) and has_ancestor(i, h_pdg, pdg_ids, mothers):
                h_leptons.append(i)
        if abs_id == 5 and has_ancestor(i, y_pdg, pdg_ids, mothers):
            y_b_quarks.append(i)

    return {
        "has_xyh": has_xyh,
        "has_ybb": has_ybb,
        "has_h4l": len(h_leptons) >= 4,
        "n_h_leptons": len(h_leptons),
        "n_y_b_quarks": len(y_b_quarks),
        "valid_signal": has_xyh and has_ybb and len(h_leptons) >= 4,
    }

