"""Ground objects: is this a person, an animal or a vehicle?

Does:
    Takes the observations several ground sensors made of one object over a short
    window (thermal array, low-power radar, PIR, a camera's own analytics) and
    returns a label in {human, animal, vehicle, unknown}, a confidence, and which
    sensor types contributed. Every feature is something a sensor measured:
    apparent height and width, speed, limb-motion cadence, a camera's label.

Does NOT do:
    Detect anything itself, track objects, or decide an alarm (policy.py does,
    and it requires two sensor types). It does not identify people: no faces, no
    devices, no personal data. It does not claim a false-alarm rate: nothing here
    has been tested against a real fence, a real fox or a real person.

IMPORTANT — HONESTY CONSTRAINT:
    The rules below are ENGINEERING PRIORS, not fitted to data. Published radar
    studies separate people from animals with learned models on full Doppler
    spectrograms (see research/sources.md); these hand rules use only the
    cadence and the speed, so they will be weaker. Known failure modes, by design
    of the features: a person crawling looks like an animal to the thermal shape
    rule, and a trotting dog has a cadence close to a walking person. Replace the
    priors with fitted values once the ground tests in product/perimeter.md run.
"""

from __future__ import annotations

from .geometry import HUMAN_MAX_FOOT_SPEED_MPS, HUMAN_STEP_HZ, HUMAN_UPRIGHT_HEIGHT_M

GROUND_CLASSIFIER_VERSION = "ground-v0-priors-not-fitted"
CLASSES = ("human", "animal", "vehicle")

# A shape needs resolution: at this range, an upright person must span at least
# this many pixels, or the blob says "something warm is there" and nothing about
# what it is. A two-pixel fox at 10 m is still evidence (a person would be five
# pixels there); a two-pixel blob at 40 m is not. Prior, not measured.
MIN_PIXELS_FOR_SHAPE = 3

# Labels a camera's built-in analytics may emit, mapped to our classes.
CAMERA_LABELS = {
    "person": "human",
    "human": "human",
    "vehicle": "vehicle",
    "car": "vehicle",
    "truck": "vehicle",
    "animal": "animal",
}

# Radar evidence is capped: cadence alone does not separate a walking person
# from a trotting dog, so radar can lean but never decide on its own.
RADAR_HUMAN_WEIGHT = 0.7


def ramp(x: float, lo: float, hi: float) -> float:
    """0 below lo, 1 above hi, linear in between."""
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (x - lo) / (hi - lo)


def trapezoid(x: float, a: float, b: float, c: float, d: float) -> float:
    """1 between b and c, falling linearly to 0 at a and d."""
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)


def _normalise(scores: dict) -> dict | None:
    total = sum(scores.values())
    if total <= 1e-9:
        return None
    return {k: v / total for k, v in scores.items()}


def thermal_evidence(obs: dict) -> dict | None:
    """Shape from a thermal blob: people are tall and narrow, quadrupeds low and
    long, vehicles big. None when the sensor cannot resolve a person's shape at
    this range (obs["pixel_m"], the vertical size of one pixel there) or, without
    that, when the blob itself is fewer than MIN_PIXELS_FOR_SHAPE pixels tall."""
    pixel_m = obs.get("pixel_m")
    if pixel_m is not None:
        if HUMAN_UPRIGHT_HEIGHT_M[0] / max(float(pixel_m), 1e-6) < MIN_PIXELS_FOR_SHAPE:
            return None
    elif obs.get("pixels_tall", 0) < MIN_PIXELS_FOR_SHAPE:
        return None
    h = float(obs["height_m"])
    w = max(float(obs["width_m"]), 0.05)
    aspect = h / w
    h_lo, h_hi = HUMAN_UPRIGHT_HEIGHT_M
    human = trapezoid(h, h_lo - 0.2, h_lo, h_hi, h_hi + 0.3) * ramp(aspect, 1.1, 1.6)
    animal = (1.0 - ramp(h, 1.0, 1.4)) * (1.0 - ramp(aspect, 0.9, 1.4))
    vehicle = ramp(w, 1.4, 2.5) * ramp(h, 0.9, 1.3)
    return _normalise({"human": human, "animal": animal, "vehicle": vehicle})


def radar_evidence(obs: dict) -> dict | None:
    """Speed plus limb-motion cadence. No cadence and real speed means a vehicle;
    a cadence in the human walking band leans human; anything else leans animal."""
    speed = float(obs.get("speed_mps", 0.0))
    gait = obs.get("gait_hz")
    if gait is None:
        if speed < 0.3:
            return None
        return _normalise({"human": 0.0, "animal": 0.0, "vehicle": ramp(speed, 1.5, 4.0)})
    step_lo, step_hi = HUMAN_STEP_HZ
    human_like = trapezoid(float(gait), step_lo - 0.2, step_lo, step_hi, step_hi + 0.5)
    human_like *= 1.0 - ramp(speed, HUMAN_MAX_FOOT_SPEED_MPS - 2.5, HUMAN_MAX_FOOT_SPEED_MPS)
    human = RADAR_HUMAN_WEIGHT * human_like
    animal = (1.0 - RADAR_HUMAN_WEIGHT) * human_like + 0.8 * (1.0 - human_like)
    return _normalise({"human": human, "animal": animal, "vehicle": 0.0})


def camera_evidence(obs: dict) -> dict | None:
    """A camera's own analytics label, taken at its stated score."""
    label = CAMERA_LABELS.get(str(obs.get("label", "")).lower())
    if label is None:
        return None
    score = max(0.0, min(1.0, float(obs.get("score", 0.5))))
    rest = (1.0 - score) / 2.0
    return {k: (score if k == label else rest) for k in CLASSES}


EVIDENCE = {
    "thermal": thermal_evidence,
    "radar_mmwave": radar_evidence,
    "camera_ai": camera_evidence,
    # "pir" is presence only: it counts as a sensor that saw the object, but it
    # carries no information about what the object is.
}


def classify_track(observations: list[dict]) -> dict:
    """Classify one ground object from all observations of it in a window.

    Each sensor type gets one equal vote (the mean of its observations), so ten
    frames from one camera cannot outvote one thermal sensor. Label is "unknown"
    unless the top class has at least half the probability and a clear margin.
    Confidence is reduced when the sensor types disagree, and when only one
    informative sensor type contributed.
    """
    present = sorted({o.get("sensor", "?") for o in observations})
    per_type: dict[str, list[dict]] = {}
    for obs in observations:
        fn = EVIDENCE.get(obs.get("sensor"))
        if fn is None:
            continue
        ev = fn(obs)
        if ev is not None:
            per_type.setdefault(obs["sensor"], []).append(ev)

    type_means = {
        t: {k: sum(ev[k] for ev in evs) / len(evs) for k in CLASSES}
        for t, evs in per_type.items()
    }

    base = {
        "version": GROUND_CLASSIFIER_VERSION,
        "sensor_types": present,
        "informative_types": sorted(type_means),
        "n_observations": len(observations),
        "per_type": {t: {k: round(v, 3) for k, v in m.items()} for t, m in type_means.items()},
        "disclaimer": (
            "rules are engineering priors, not fitted to field data; "
            "confidence is an estimate"
        ),
    }
    if not type_means:
        return {**base, "label": "unknown", "confidence": 0.0, "probs": {}}

    probs = {k: sum(m[k] for m in type_means.values()) / len(type_means) for k in CLASSES}
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    (top, p_top), (_, p_second) = ranked[0], ranked[1]

    label = top if p_top >= 0.5 and p_top - p_second >= 0.2 else "unknown"
    if label == "unknown":
        confidence = 0.0
    else:
        votes = [max(m, key=m.get) for m in type_means.values()]
        agreement = votes.count(label) / len(votes)
        single = 0.75 if len(type_means) == 1 else 1.0
        confidence = p_top * agreement * single

    return {
        **base,
        "label": label,
        "confidence": round(confidence, 3),
        "probs": {k: round(v, 3) for k, v in probs.items()},
    }
