"""Alarm policy: when does a detection become an alarm?

Does:
    Turns scored detections into (or not into) an alarm, applying thresholds,
    a cooldown so one drone is not fifty alarms, a whitelist for known authorised
    flights, and a confidence floor.

Does NOT do:
    Decide any legal question. Whether a drone may be neutralised is a judgement
    made by a human under Prawo lotnicze art. 156ze (see ../research/legal-pl.md).
    This module must never be described as making that call, and must never emit
    anything that could be read as an authorisation to act.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class AlarmPolicy:
    """Thresholds for raising an alarm. Defaults are engineering priors.

    Every default here is a guess to be replaced by measurement (T-5 gives the
    false-positive rate; T-6 gives the position accuracy). Changing a default
    requires writing the reason into hardware/results.md.
    """

    min_confidence: float = 0.60
    min_snr_db: float = 6.0
    require_drone_like: bool = True
    cooldown_seconds: int = 60
    repeat_alarm_after_seconds: int = 300
    track_ttl_seconds: int = 30


@dataclass
class Whitelist:
    """Authorised flights, so a known friendly drone does not alarm a site.

    Entries are simple: a frequency in MHz, an optional time window, an optional
    comment. Keep it dumb and inspectable — a security officer must be able to read
    and edit this file without help.
    """

    entries: list[dict] = field(default_factory=list)

    def matches(self, freq_hz: float, when: datetime | None = None) -> dict | None:
        when = when or datetime.now(timezone.utc)
        freq_mhz = freq_hz / 1e6
        for entry in self.entries:
            center = entry.get("freq_mhz")
            if center is None:
                continue
            tolerance = entry.get("tolerance_mhz", 2.0)
            if abs(freq_mhz - center) > tolerance:
                continue
            start = entry.get("from_utc")
            end = entry.get("to_utc")
            if start and when < datetime.fromisoformat(start):
                continue
            if end and when > datetime.fromisoformat(end):
                continue
            return entry
        return None


class AlarmState:
    """Tracks cooldowns and recent alarms. In-memory; the event log is durable."""

    def __init__(self, policy: AlarmPolicy, whitelist: Whitelist | None = None) -> None:
        self.policy = policy
        self.whitelist = whitelist or Whitelist()
        self._last_alarm: dict[str, datetime] = {}
        self._alarm_counts: dict[str, int] = {}

    def _bucket(self, key: str) -> str:
        return key

    def evaluate(
        self,
        detection: dict,
        node_id: str,
        when: datetime | None = None,
    ) -> dict:
        """Decide whether this detection alarms.

        detection: dict with at least freq_hz, snr_db, confidence, classification.
        Returns a decision dict explaining the outcome, never a bare boolean, so
        the operator record can show why nothing happened.
        """
        when = when or datetime.now(timezone.utc)
        reasons: list[str] = []

        entry = self.whitelist.matches(detection["freq_hz"], when)
        if entry is not None:
            return {
                "alarm": False,
                "suppressed": True,
                "reason": "whitelisted_authorised_flight",
                "whitelist_entry": entry.get("comment", ""),
                "ts_utc": when.isoformat(),
            }

        if detection.get("snr_db", 0.0) < self.policy.min_snr_db:
            reasons.append("below_snr_threshold")
        if detection.get("confidence", 0.0) < self.policy.min_confidence:
            reasons.append("below_confidence_threshold")
        if self.policy.require_drone_like and detection.get("classification") != "drone_like":
            reasons.append("not_classified_drone_like")

        if reasons:
            return {
                "alarm": False,
                "suppressed": False,
                "reason": ",".join(reasons),
                "ts_utc": when.isoformat(),
            }

        key = self._bucket(f"{node_id}:{round(detection['freq_hz'] / 1e6)}")
        last = self._last_alarm.get(key)
        if last is not None:
            elapsed = (when - last).total_seconds()
            if elapsed < self.policy.cooldown_seconds:
                return {
                    "alarm": False,
                    "suppressed": True,
                    "reason": f"cooldown_active({int(elapsed)}s)",
                    "ts_utc": when.isoformat(),
                }
            if elapsed < self.policy.repeat_alarm_after_seconds:
                return {
                    "alarm": False,
                    "suppressed": True,
                    "reason": "already_alarmed_recently",
                    "ts_utc": when.isoformat(),
                }

        self._last_alarm[key] = when
        self._alarm_counts[key] = self._alarm_counts.get(key, 0) + 1
        return {
            "alarm": True,
            "suppressed": False,
            "reason": "thresholds_met",
            "repeat_of": self._alarm_counts[key] - 1,
            "ts_utc": when.isoformat(),
            "action_note": (
                "Human decision required. Check whether an authorised flight is "
                "known, then follow the site's escalation procedure. This system "
                "does not authorise or perform any countermeasure."
            ),
        }

    @property
    def alarm_counts(self) -> dict[str, int]:
        return dict(self._alarm_counts)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def within_cooldown(last: datetime | None, seconds: int, now: datetime) -> bool:
    if last is None:
        return False
    return (now - last) < timedelta(seconds=seconds)
