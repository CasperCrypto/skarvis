"""CZAPLA — passive counter-drone detection.

What this package does:
    Detects drone radio links passively, estimates the direction they come from,
    merges detections from several nodes into a position, raises an alarm under a
    documented policy, and writes an evidence record plus a Polish incident report.

What this package explicitly does NOT do:
    It never transmits. No jamming, spoofing, GNSS interference, capture or
    kinetic function exists anywhere in this codebase, and none may be added.
    See ../research/legal-pl.md for why that is a hard constraint.

Dependency policy: standard library only, so the Raspberry Pi node and a
development laptop behave identically.
"""

__version__ = "0.1.0"
SCHEMA_EVENT = "czapla.event/1"
SCHEMA_POSITION = "czapla.position/1"
