"""Fusion: merge detections from several nodes into a position estimate.

Does:
    Groups detections that plausibly belong to the same drone (close in time and
    in frequency), and triangulates the bearings of nodes that saw it.

Does NOT do:
    Track a drone over minutes, or identify it. Tracks beyond a short TTL are v2
    work; pretending to track a drone we cannot see continuously would be a false
    claim. This module deliberately keeps only what two bearings support.
"""

from __future__ import annotations

import math

from .geometry import (
    cep_from_ray_sigma,
    latlon_to_local,
    local_to_latlon,
    triangulate,
)


def group_detections(
    detections: list[dict],
    time_window_s: float = 5.0,
    freq_tolerance_mhz: float = 20.0,
) -> list[list[dict]]:
    """Group detections that could be the same drone.

    Two detections belong together when they are close in time and close in
    frequency. This is deliberately crude: a wrong grouping produces a bad fix,
    which shows up as a large spread_m in the triangulation and gets rejected,
    rather than as a confident wrong position.
    """
    used = [False] * len(detections)
    groups: list[list[dict]] = []

    def ts(d: dict) -> float:
        raw = d.get("ts_utc", "")
        try:
            from datetime import datetime

            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0

    order = sorted(range(len(detections)), key=lambda i: ts(detections[i]))
    for a in order:
        if used[a]:
            continue
        group = [detections[a]]
        used[a] = True
        for b in order:
            if used[b]:
                continue
            if abs(ts(detections[b]) - ts(detections[a])) > time_window_s:
                continue
            f_a = detections[a].get("band_mhz") or detections[a]["freq_hz"] / 1e6
            f_b = detections[b].get("band_mhz") or detections[b]["freq_hz"] / 1e6
            if abs(f_a - f_b) > freq_tolerance_mhz:
                continue
            group.append(detections[b])
            used[b] = True
        groups.append(group)
    return groups


def fuse_group(
    group: list[dict],
    ref_lat: float,
    ref_lon: float,
    max_spread_m: float = 150.0,
    max_bearing_sigma_deg: float = 25.0,
) -> dict | None:
    """Triangulate one group into a lat/lon, or return None with a reason.

    Rejects rather than guesses:
      - fewer than two usable bearings -> no fix
      - any bearing with sigma above the threshold -> geometry too poor
      - spread above max_spread_m -> the rays do not agree, do not publish a point
    """
    rays: list[tuple[float, float, float]] = []
    sigmas: list[float] = []
    sources: list[str] = []
    for det in group:
        bearing = det.get("bearing_deg")
        pos = det.get("node_position")
        if bearing is None or not pos:
            continue
        sigma = det.get("bearing_sigma_deg")
        if sigma is not None and sigma > max_bearing_sigma_deg:
            continue
        east, north = latlon_to_local(pos["lat"], pos["lon"], ref_lat, ref_lon)
        rays.append((east, north, float(bearing)))
        sigmas.append(float(sigma) if sigma is not None else 10.0)
        sources.append(det.get("node_id", "unknown"))

    if len(rays) < 2 or len(set(sources)) < 2:
        return {"fused": False, "reason": "need_bearings_from_two_distinct_nodes"}

    fix = triangulate(rays)
    if fix is None:
        return {"fused": False, "reason": "degenerate_geometry_rays_parallel"}

    if fix["spread_m"] > max_spread_m:
        return {
            "fused": False,
            "reason": "rays_disagree",
            "spread_m": fix["spread_m"],
            "max_spread_m": max_spread_m,
        }

    lat, lon = local_to_latlon(fix["east"], fix["north"], ref_lat, ref_lon)
    mean_sigma = sum(sigmas) / len(sigmas)
    uncertainty = cep_from_ray_sigma(rays, mean_sigma)

    # Confidence combines geometry quality with how well the rays agree.
    agreement = max(0.0, 1.0 - fix["spread_m"] / max_spread_m)
    confidence = round(min(1.0, 0.5 * fix["quality"] + 0.5 * agreement), 3)

    return {
        "fused": True,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "sources": sources,
        "quality": fix["quality"],
        "spread_m": fix["spread_m"],
        "worst_pair_angle_deg": fix["worst_pair_angle_deg"],
        "cep_estimate_m": uncertainty.get("sensitivity_m"),
        "confidence": confidence,
        "n_rays": fix["n_rays"],
    }


def fuse_all(
    detections: list[dict], ref_lat: float, ref_lon: float, **kwargs
) -> list[dict]:
    """Group then fuse. Returns only the groups that produced a fix, plus rejects."""
    results: list[dict] = []
    for group in group_detections(detections):
        outcome = fuse_group(group, ref_lat, ref_lon, **kwargs)
        if outcome is None:
            continue
        outcome["group_size"] = len(group)
        results.append(outcome)
    return results


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres. Used to score a fix against ground truth."""
    earth = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * earth * math.asin(min(1.0, math.sqrt(a)))
