"""Geometry, bearings and triangulation.

Does:
    Angle helpers, circular statistics for bearings, local-plane coordinate
    conversion, and least-squares triangulation of bearing rays into a position.

Does NOT do:
    Own any threshold, policy or sensor logic. Constants used by physics/geometry
    live here; alarm policy lives in policy.py.
"""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_008.8


def wrap_deg(angle_deg: float) -> float:
    """Normalise an angle to [0, 360)."""
    return angle_deg % 360.0


def wrap_180(angle_deg: float) -> float:
    """Normalise an angle to (-180, 180]. Use for differences."""
    a = (angle_deg + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def bearing_to_unit(bearing_deg: float) -> tuple[float, float]:
    """Compass bearing (0=N, 90=E) to a unit vector in a local ENU plane.

    Returns (east, north). Note this is a *compass* convention, so it differs
    from the mathematical atan2 convention: 0 degrees points north (+y).
    """
    r = math.radians(bearing_deg)
    return (math.sin(r), math.cos(r))


def unit_to_bearing(east: float, north: float) -> float:
    """Inverse of bearing_to_unit."""
    return wrap_deg(math.degrees(math.atan2(east, north)))


def circular_mean_deg(angles_deg: list[float]) -> float:
    """Mean of angles, correctly handling wraparound (350 and 10 -> 0)."""
    if not angles_deg:
        raise ValueError("circular_mean_deg needs at least one angle")
    s = sum(math.sin(math.radians(a)) for a in angles_deg)
    c = sum(math.cos(math.radians(a)) for a in angles_deg)
    if abs(s) < 1e-12 and abs(c) < 1e-12:
        raise ValueError("angles are uniformly spread; no meaningful mean")
    return wrap_deg(math.degrees(math.atan2(s, c)))


def circular_std_deg(angles_deg: list[float]) -> float:
    """Circular standard deviation in degrees. Small = stable bearing."""
    if len(angles_deg) < 2:
        return 0.0
    angles = [math.radians(a) for a in angles_deg]
    s = sum(math.sin(a) for a in angles) / len(angles)
    c = sum(math.cos(a) for a in angles) / len(angles)
    r = math.hypot(s, c)
    r = min(1.0, max(r, 1e-12))
    return math.degrees(math.sqrt(-2.0 * math.log(r)))


def latlon_to_local(
    lat: float, lon: float, lat0: float, lon0: float
) -> tuple[float, float]:
    """Approximate a lat/lon as metres east/north of a reference point.

    Equirectangular approximation: fine over the few hundred metres a single site
    covers, wrong over kilometres. Do not use for map-scale work.
    """
    east = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * EARTH_RADIUS_M
    return (east, north)


def local_to_latlon(
    east: float, north: float, lat0: float, lon0: float
) -> tuple[float, float]:
    """Inverse of latlon_to_local."""
    lat = lat0 + math.degrees(north / EARTH_RADIUS_M)
    lon = lon0 + math.degrees(east / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    return (lat, lon)


def triangulate(rays: list[tuple[float, float, float]]) -> dict | None:
    """Least-squares intersection of bearing rays into a position.

    rays: list of (east_m, north_m, bearing_deg).

    Method: minimise the sum of squared perpendicular distances from the candidate
    point to each ray. That is an ordinary least-squares problem whose normal
    equations are 2x2, so it is solved directly. Exactly intersecting rays give
    cost 0 at the intersection, so for two clean rays this returns the intersection.

    Returns dict with east, north, quality, n_rays, spread_m — or None when the
    geometry is degenerate (all rays parallel, fewer than two rays).
    """
    if len(rays) < 2:
        return None

    # Sum of projection matrices M_i = I - d d^T, and M_i * p_i.
    a11 = a12 = a22 = b1 = b2 = 0.0
    dirs: list[tuple[float, float]] = []
    for east, north, bearing in rays:
        de, dn = bearing_to_unit(bearing)
        dirs.append((de, dn))
        m11, m12, m22 = 1.0 - de * de, -de * dn, 1.0 - dn * dn
        a11 += m11
        a12 += m12
        a22 += m22
        b1 += m11 * east + m12 * north
        b2 += m12 * east + m22 * north

    det = a11 * a22 - a12 * a12
    # det is zero when every ray points along the same line (no fix possible).
    if abs(det) < 1e-9:
        return None

    east = (b1 * a22 - b2 * a12) / det
    north = (a11 * b2 - a12 * b1) / det

    # Geometry quality, scale-invariant: M = sum(I - d d^T) has trace n, and both
    # eigenvalues equal n/2 when the rays are perfectly spread. So the smaller
    # eigenvalue divided by n/2 runs 0 (all rays parallel, no fix) to 1 (ideal
    # spread), regardless of how many nodes there are. Using the minimum pairwise
    # angle instead would wrongly punish a 3-node set that contains one pair of
    # nearly-parallel rays while still resolving the position well.
    n = len(rays)
    disc = n * n - 4.0 * det
    min_eigenvalue = (n - math.sqrt(max(0.0, disc))) / 2.0
    quality = min(1.0, max(0.0, min_eigenvalue / (n / 2.0)))

    worst_pair_angle = 180.0
    for i in range(len(dirs)):
        for j in range(i + 1, len(dirs)):
            cross = dirs[i][0] * dirs[j][1] - dirs[i][1] * dirs[j][0]
            angle = abs(math.degrees(math.asin(max(-1.0, min(1.0, cross)))))
            worst_pair_angle = min(worst_pair_angle, angle)

    residuals = []
    for ray_east, ray_north, bearing in rays:
        de, dn = bearing_to_unit(bearing)
        vx, vy = east - ray_east, north - ray_north
        perp = abs(vx * dn - vy * de)  # perpendicular distance to the ray
        residuals.append(perp)
    spread = math.sqrt(sum(r * r for r in residuals) / len(residuals))

    return {
        "east": east,
        "north": north,
        "quality": round(quality, 4),
        "worst_pair_angle_deg": round(worst_pair_angle, 2),
        "n_rays": n,
        "spread_m": round(spread, 2),
    }


def cep_from_ray_sigma(
    rays: list[tuple[float, float, float]], sigma_deg: float, cep_m: float = 100.0
) -> dict:
    """Rough uncertainty estimate: how much the fix moves if each bearing is off.

    Perturbs every bearing by +sigma and -sigma, retriangulates, and reports the
    displacement. This is a sensitivity check, not a rigorous CEP, and is labelled
    as an estimate everywhere it is reported.
    """
    base = triangulate(rays)
    if base is None:
        return {"estimate": True, "cep_m": None, "note": "no fix possible"}

    shifts = []
    for sign in (1.0, -1.0):
        moved = triangulate([(e, n, b + sign * sigma_deg) for e, n, b in rays])
        if moved is not None:
            shifts.append(
                math.hypot(moved["east"] - base["east"], moved["north"] - base["north"])
            )
    worst = max(shifts) if shifts else None
    return {
        "estimate": True,
        "base_east": round(base["east"], 2),
        "base_north": round(base["north"], 2),
        "sensitivity_m": round(worst, 2) if worst is not None else None,
        "selected_cep_m": cep_m,
        "note": "sensitivity to a +-sigma bearing error, not a true CEP",
    }


# --- Sensor and target reference constants -------------------------------------
# Sources are in ../research/sources.md. Anything not sourced is marked ESTIMATE
# and must be replaced by a measured number before it reaches a buyer.

# KrakenSDR tuning range (krakenrf.com product page). It cannot hear 2.4/5.8 GHz.
KRAKENSDR_MIN_MHZ = 24.0
KRAKENSDR_MAX_MHZ = 1766.0

# Free-space path loss slope: received power falls 20 dB per decade of distance.
FSPL_DB_PER_DECADE = 20.0

# MLX90640 thermal array (Melexis datasheet): 32 x 24 pixels, 55 x 35 deg variant.
MLX90640_PIXELS_H = 32
MLX90640_PIXELS_V = 24
MLX90640_FOV_H_DEG = 55.0
MLX90640_FOV_V_DEG = 35.0

# Human walking cadence (Tudor-Locke & Rowe 2012: 81-138 steps/min in the lab).
# Walking speed for scenario actors: 1.1-1.4 m/s (Bohannon & Andrews 2011).
HUMAN_STEP_HZ = (1.3, 2.3)

# ESTIMATE, not sourced: apparent upright height of an adult, and the point above
# which a moving object is too fast to be walking or jogging.
HUMAN_UPRIGHT_HEIGHT_M = (1.3, 2.1)
HUMAN_MAX_FOOT_SPEED_MPS = 6.0


def point_in_polygon(east: float, north: float, polygon: list) -> bool:
    """True when (east, north) is inside the polygon (list of [east, north]).

    Ray casting. Points exactly on an edge may go either way; a perimeter alarm
    that depends on centimetres at the fence line is not a decision this
    function should be trusted with.
    """
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        ei, ni = polygon[i][0], polygon[i][1]
        ej, nj = polygon[j][0], polygon[j][1]
        if (ni > north) != (nj > north):
            cross_e = ei + (north - ni) * (ej - ei) / (nj - ni)
            if east < cross_e:
                inside = not inside
        j = i
    return inside


def pixel_footprint_m(range_m: float, fov_deg: float, pixels: int) -> float:
    """Size in metres that one sensor pixel covers at a given range.

    This is why a cheap 32x24 thermal array can tell a person from a fox at 15 m
    and cannot at 50 m: at long range the whole person fits in one pixel.
    """
    if pixels <= 0:
        raise ValueError("pixels must be positive")
    return max(0.0, range_m) * math.tan(math.radians(fov_deg / pixels))


def path_snr_db(ref_snr_db: float, ref_dist_m: float, dist_m: float) -> float:
    """Free-space SNR scaling from a reference point. Ignores terrain and multipath.

    The reference (e.g. "30 dB at 100 m") is an assumption until T-2/T-6 measure it.
    """
    dist_m = max(dist_m, 1.0)
    return ref_snr_db - FSPL_DB_PER_DECADE * math.log10(dist_m / max(ref_dist_m, 1.0))
