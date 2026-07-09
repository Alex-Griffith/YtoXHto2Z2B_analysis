import math


def delta_phi(a, b):
    value = a - b
    while value > math.pi:
        value -= 2.0 * math.pi
    while value <= -math.pi:
        value += 2.0 * math.pi
    return value


def delta_r(a, b):
    return math.hypot(a["eta"] - b["eta"], delta_phi(a["phi"], b["phi"]))


def p4(obj):
    pt, eta, phi, mass = obj["pt"], obj["eta"], obj["phi"], obj["mass"]
    px, py = pt * math.cos(phi), pt * math.sin(phi)
    pz = pt * math.sinh(eta)
    energy = math.sqrt(max(0.0, px * px + py * py + pz * pz + mass * mass))
    return px, py, pz, energy


def add(*objects):
    px = py = pz = energy = 0.0
    for obj in objects:
        x, y, z, e = p4(obj)
        px += x; py += y; pz += z; energy += e
    pt = math.hypot(px, py)
    momentum = math.sqrt(px * px + py * py + pz * pz)
    mass = math.sqrt(max(0.0, energy * energy - momentum * momentum))
    eta = math.asinh(pz / pt) if pt > 0 else 0.0
    phi = math.atan2(py, px)
    rapidity = 0.5 * math.log((energy + pz) / (energy - pz)) if energy > abs(pz) else 0.0
    return {"pt": pt, "eta": eta, "phi": phi, "mass": mass, "rapidity": rapidity}
