"""Persistence baseline: telling infrastructure apart from a drone.

Does:
    Remembers which frequencies are occupied in almost every scan. A Wi-Fi access
    point, a DECT base or a fixed video link is present in every single scan, all
    day. A drone appears and then goes away. That difference is the only
    discriminator v1 has for one specific confusion, and it is an important one.

Does NOT do:
    Learn a full spectrum model, or detect anything. This is bookkeeping over
    observations the detector already produced.

Why this module exists:
    A single snapshot cannot separate a wide infrastructure carrier from a wide
    drone video downlink — both are just wideband energy in a drone band. Claiming
    otherwise would be the exact overclaiming this project forbids. So the product
    claim is narrower and true: a signal present continuously for minutes is
    infrastructure; a signal that appears and disappears is what we alarm on.
"""

from __future__ import annotations

from collections import deque


class BaselineTracker:
    """Rolling occupancy history per frequency.

    occupancy(f) = fraction of recent scans in which some detection sat within
    tolerance_mhz of f. The tracker is only trusted after min_observations scans,
    so a fresh start cannot declare the first drone it ever sees "infrastructure".
    """

    def __init__(
        self,
        window: int = 20,
        occupancy_threshold: float = 0.8,
        tolerance_mhz: float = 5.0,
        min_observations: int = 5,
    ) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        if not 0.0 < occupancy_threshold <= 1.0:
            raise ValueError("occupancy_threshold must be in (0, 1]")
        self.window = window
        self.occupancy_threshold = occupancy_threshold
        self.tolerance_mhz = tolerance_mhz
        self.min_observations = max(1, min_observations)
        self._history: deque[list[float]] = deque(maxlen=window)

    @property
    def observation_count(self) -> int:
        return len(self._history)

    @property
    def is_trusted(self) -> bool:
        """True once enough scans have been seen for the baseline to mean anything."""
        return len(self._history) >= self.min_observations

    def observe(self, frequencies_mhz: list[float]) -> None:
        """Record one scan's detected centre frequencies."""
        self._history.append([float(f) for f in frequencies_mhz])

    def occupancy(self, freq_mhz: float) -> float:
        """Fraction of recent scans containing a detection near freq_mhz."""
        if not self._history:
            return 0.0
        hits = 0
        for scan in self._history:
            if any(abs(f - freq_mhz) <= self.tolerance_mhz for f in scan):
                hits += 1
        return hits / len(self._history)

    def is_persistent(self, freq_mhz: float) -> bool:
        """True when the baseline is trusted AND this frequency looks like infrastructure."""
        if not self.is_trusted:
            return False
        return self.occupancy(freq_mhz) >= self.occupancy_threshold

    def reset(self) -> None:
        self._history.clear()
