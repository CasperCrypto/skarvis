"""Classification: is this detection drone-like?

Does:
    Scores a detection using explicitly listed features and returns a label plus a
    confidence and the reasons. Every feature is something the sensor actually
    measured — nothing is inferred from a model we cannot show.

Does NOT do:
    Claim certainty, and never overrides policy. A high score here is one input to
    the alarm decision, not the decision. There is no machine learning in v1 on
    purpose: an unexplainable alarm is unusable in a security room and un-auditable
    in a defence procurement.

IMPORTANT — HONESTY CONSTRAINT:
    The feature weights below are ENGINEERING PRIORS, not fitted to data. There is
    no labelled dataset of drone versus Wi-Fi in this project yet. They must be
    replaced by fitted values once field data exists (see hardware/test-plan.md,
    T-2 and T-5), and until then the confidence this module returns is an estimate.
"""

from __future__ import annotations

CLASSIFIER_VERSION = "v1-priors-not-fitted"

# Frequencies where consumer drone control and video links are commonly found.
# Sources are public band allocations, not vendor data.
#
# 2026-10-28: the KrakenSDR (24-1766 MHz) cannot hear 2.4/5.8 GHz, so with only
# the 2.4/5.8 GHz centres every Kraken detection was band-gated to "other" and
# could never alarm (found by running czapla.sim). Added, sources in
# research/sources.md:
#   433.05-434.79 MHz and 863-870 MHz  SRD bands used by long-range control links
#                                      (ExpressLRS and similar). Narrow windows
#                                      on purpose: mobile-phone uplinks sit just
#                                      outside them and must not get band credit.
#                                      915 MHz (US ISM) is left out for the same
#                                      reason: in Poland that range is phone uplink.
#   1080-1360 MHz                      1.2 GHz analog FPV video, 8 channels 40 MHz
#                                      apart. Also holds GNSS (below the noise
#                                      floor) and L-band air-surveillance radar;
#                                      T-5 measures what that costs.
# Each band: (centre MHz, full-credit half-width, zero-credit half-width).
FPV_1G2_VIDEO_CHANNELS_MHZ = (1080.0, 1120.0, 1160.0, 1200.0, 1240.0, 1280.0, 1320.0, 1360.0)
WIFI_LIKE_DRONE_CENTERS_MHZ = (2437.0, 2452.0, 2462.0, 2477.0, 5800.0)
DRONE_BANDS = (
    ((433.92, 0.87, 2.0), (866.5, 3.5, 4.5))
    + tuple((c, 5.0, 20.0) for c in FPV_1G2_VIDEO_CHANNELS_MHZ)
    + tuple((c, 5.0, 20.0) for c in WIFI_LIKE_DRONE_CENTERS_MHZ)
)
DRONE_BAND_CENTERS_MHZ = tuple(band[0] for band in DRONE_BANDS)

# Bandwidth signatures, calibrated against what a synthesised carrier actually
# measures through a Hann window: a steady carrier spreads to a few FFT bins, so its
# measured width is thousands of hertz, not zero. Anything at or below a few tens of
# kHz is a narrow emission; tens of MHz is flight-video-like.
NARROW_WIDTH_HZ = 200_000.0
WIDE_WIDTH_HZ = 6_000_000.0

# Weights are engineering priors. Sum to 1.0 so the score stays in [0, 1].
W_SNR = 0.35
W_BAND = 0.25
W_WIDTH = 0.20
W_FHOP = 0.20


def band_affinity_mhz(freq_mhz: float) -> float:
    """How close a frequency is to a known drone band. 1.0 = inside the band."""
    best = 0.0
    for center, full, zero in DRONE_BANDS:
        delta = abs(freq_mhz - center)
        # Full credit within the band, fading linearly to none at the zero edge.
        if delta <= full:
            score = 1.0
        elif delta >= zero:
            score = 0.0
        else:
            score = 1.0 - (delta - full) / (zero - full)
        best = max(best, score)
    return best


def width_score(width_hz: float) -> float:
    """Drone-like if the emission is either clearly narrow or clearly wide.

    Consumer RC control links are narrow; video downlinks are wide. A mid-width
    emission is more characteristic of Wi-Fi or a generic data link.
    """
    if width_hz <= NARROW_WIDTH_HZ:
        return 0.8
    if width_hz >= WIDE_WIDTH_HZ:
        return 1.0
    return 0.3


def classify(
    snr_db: float,
    freq_hz: float,
    width_hz: float,
    freq_hop_count: int = 0,
    band_mhz: float | None = None,
) -> dict:
    """Score one detection as drone-like.

    freq_hop_count: number of distinct centre frequencies observed for this signal
    within the observation window. Frequency hopping between a few channels is
    characteristic of a control link; a stationary Wi-Fi access point scores 0.

    Returns label in {"drone_like", "unknown", "other"}, a 0-1 score, the
    confidence, and the per-feature contributions so a security officer can see
    why the alarm fired.

    Hard gate: a signal outside every known consumer drone band can never be
    labelled drone_like, whatever else it looks like. Drones have to be in a drone
    band to control or stream from the drone, so this gate removes a whole class of
    false positives at zero cost in missed detections.
    """
    freq_mhz = freq_hz / 1e6
    affinity = band_affinity_mhz(freq_mhz)
    w_score = width_score(width_hz)
    snr_score = max(0.0, min(1.0, snr_db / 25.0))
    if freq_hop_count >= 3:
        hop_score = 1.0
    elif freq_hop_count == 2:
        hop_score = 0.6
    elif freq_hop_count == 1:
        hop_score = 0.2
    else:
        hop_score = 0.0

    score = (
        W_SNR * snr_score
        + W_BAND * affinity
        + W_WIDTH * w_score
        + W_FHOP * hop_score
    )
    gated = affinity <= 0.0
    if gated:
        # Clamp below the drone_like boundary; see the hard gate note above.
        score = min(score, 0.39)
    score = max(0.0, min(1.0, score))


    if score >= 0.70:
        label = "drone_like"
    elif score >= 0.40:
        label = "unknown"
    else:
        label = "other"

    # Confidence: how far the score sits from the nearest decision boundary, so a
    # marginal case reports low confidence rather than a confident wrong answer.
    boundary = 0.70 if label == "drone_like" else (0.40 if label == "unknown" else 0.40)
    confidence = min(1.0, abs(score - boundary) / 0.30 + 0.5) if label != "other" else max(
        0.0, min(1.0, (0.40 - score) / 0.40)
    )

    return {
        "label": label,
        "score": round(score, 3),
        "confidence": round(max(0.0, confidence), 3),
        "version": CLASSIFIER_VERSION,
        "features": {
            "snr_score": round(snr_score, 3),
            "band_affinity": round(affinity, 3),
            "width_score": round(w_score, 3),
            "hop_score": round(hop_score, 3),
            "band_gated": gated,
        },
        "disclaimer": (
            "weights are engineering priors, not fitted to field data; "
            "confidence is an estimate"
        ),
    }
