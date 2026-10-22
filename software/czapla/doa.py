"""Direction of arrival from a five-element coherent array.

Does:
    Correlative interferometry. Given the measured phase of one signal across the
    array elements, it searches candidate bearings and returns the best match plus
    a confidence derived from how sharply the match stands out.

Does NOT do:
    Capture samples, or estimate range. A bearing is a direction, not a position:
    a position needs two nodes (see geometry.triangulate). Degrades in multipath,
    and a single compact array can only ever give an azimuth, never an elevation.
"""

from __future__ import annotations

import math

SPEED_OF_LIGHT = 299_792_458.0
DEFAULT_SEARCH_STEP_DEG = 1.0
DEFAULT_REFINE_ITERATIONS = 6


def array_element_angles(n_elements: int) -> list[float]:
    """Uniform circular array: element i sits at i * 360/n degrees.

    The array's zero mark must physically point at a known direction, and the
    software's element order must match the wiring order. If the array is wired
    clockwise and modelled anticlockwise, every bearing is mirrored.
    """
    if n_elements < 3:
        raise ValueError("an array needs at least 3 elements")
    return [i * 360.0 / n_elements for i in range(n_elements)]


def expected_phases_deg(
    bearing_deg: float,
    freq_hz: float,
    radius_m: float,
    n_elements: int = 5,
    array_yaw_deg: float = 0.0,
) -> list[float]:
    """Model phase (degrees) at each element for a plane wave from a bearing.

    Standard uniform-circular-array model: element i at angle phi_i sees extra path
    length r*cos(theta - phi_i) relative to the array centre, so its phase is
    (2*pi*r/lambda) * cos(theta - phi_i). array_yaw_deg rotates the whole array.
    """
    if freq_hz <= 0:
        raise ValueError("freq_hz must be positive")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    wavelength = SPEED_OF_LIGHT / freq_hz
    k = 2.0 * math.pi * radius_m / wavelength
    theta = math.radians(bearing_deg - array_yaw_deg)
    return [
        math.degrees(k * math.cos(theta - math.radians(phi)))
        for phi in array_element_angles(n_elements)
    ]


def _phase_residual_deg(measured: list[float], predicted: list[float]) -> float:
    """Mean squared circular residual between two phase vectors, in degrees^2."""
    total = 0.0
    for m, p in zip(measured, predicted):
        d = (m - p + 180.0) % 360.0 - 180.0
        total += d * d
    return total / len(measured)


def doa_from_phases(
    measured_phases_deg: list[float],
    freq_hz: float,
    radius_m: float,
    array_yaw_deg: float = 0.0,
    search_step_deg: float = DEFAULT_SEARCH_STEP_DEG,
    refine_iterations: int = DEFAULT_REFINE_ITERATIONS,
) -> dict:
    """Estimate the bearing by matching measured phases against the array model.

    Coarse scan over 0-360 in search_step_deg, then progressively finer bisection
    refinement around the best coarse hit. Returns the bearing, the residual, and
    a confidence: the depth of the minimum relative to the median residual across
    the whole scan. A shallow minimum means the geometry does not resolve the
    direction well, and that shows up as low confidence instead of a false fix.
    """
    if len(measured_phases_deg) < 3:
        raise ValueError("need phase from at least 3 elements")
    n_elements = len(measured_phases_deg)
    measured = list(measured_phases_deg)

    def residual(beam: float) -> float:
        return _phase_residual_deg(
            measured,
            expected_phases_deg(beam, freq_hz, radius_m, n_elements, array_yaw_deg),
        )

    step = search_step_deg
    scans: list[tuple[float, float]] = []
    beam = 0.0
    while beam < 360.0:
        scans.append((beam, residual(beam)))
        beam += step
    scans.sort(key=lambda t: t[1])
    best_beam, best_residual = scans[0]
    all_residuals = sorted(r for _, r in scans)
    median_residual = all_residuals[len(all_residuals) // 2]

    # Refine by shrinking the bracket around the best coarse hit.
    span = step
    for _ in range(refine_iterations):
        span /= 2.0
        candidates = [
            (best_beam - span, residual(best_beam - span)),
            (best_beam, best_residual),
            (best_beam + span, residual(best_beam + span)),
        ]
        candidates.sort(key=lambda t: t[1])
        best_beam, best_residual = candidates[0]

    bearing = best_beam % 360.0
    if median_residual <= 0:
        confidence = 1.0
    else:
        confidence = max(0.0, min(1.0, 1.0 - best_residual / median_residual))

    return {
        "bearing_deg": round(bearing, 2),
        "residual_deg2": round(best_residual, 4),
        "median_residual_deg2": round(median_residual, 4),
        "confidence": round(confidence, 3),
        "array_yaw_deg": array_yaw_deg,
        "n_elements": n_elements,
        "note": "azimuth only; no elevation; degrades in multipath",
    }


def bearing_sigma_from_confidence(confidence: float) -> float:
    """Bearing uncertainty in degrees implied by the DoA confidence.

    A deliberately simple mapping, documented as an estimate: a perfect match is
    treated as +-1 degree, an unresolvable one as +-30. Replace with a measured
    error distribution once T-3 and T-4 have data.
    """
    c = max(0.0, min(1.0, confidence))
    return round(1.0 + (1.0 - c) * 29.0, 2)
