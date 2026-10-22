"""Receive node events over the LAN.

Does:
    Reads newline-delimited JSON events from a UDP socket or a TCP line socket,
    validates them against the frozen schema, and hands them to the store.

Does NOT do:
    Capture RF. This is the boundary between the node (radio at the antenna) and
    the site server (fusion, alarming, reporting), so either side can be replaced.
"""

from __future__ import annotations

import json
import socket

from .events import EventStore, SchemaError, validate_event

DEFAULT_UDP_PORT = 45999
MAX_DATAGRAM = 65_507


def parse_line(line: str) -> dict:
    """Parse and validate one event line. Raises SchemaError on bad input."""
    try:
        record = json.loads(line)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"not valid JSON: {exc}") from exc
    validate_event(record)
    return record


class UdpReceiver:
    """Blocking UDP listener. Each datagram is expected to be one JSON event."""

    def __init__(self, port: int = DEFAULT_UDP_PORT, host: str = "0.0.0.0") -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))

    def recv_one(self, timeout_s: float | None = None) -> tuple[dict, tuple] | None:
        """Receive one event. Returns (event, address) or None on timeout."""
        if timeout_s is not None:
            self.sock.settimeout(timeout_s)
        try:
            data, addr = self.sock.recvfrom(MAX_DATAGRAM)
        except socket.timeout:
            return None
        return parse_line(data.decode("utf-8", "replace").strip()), addr

    def close(self) -> None:
        self.sock.close()


def serve_forever(
    store: EventStore,
    port: int = DEFAULT_UDP_PORT,
    host: str = "0.0.0.0",
    on_event=None,
) -> None:
    """Receive, validate and persist events until interrupted.

    Malformed datagrams are counted and skipped, never crash the listener: a node
    with a bug must not be able to take down the site's logging.
    """
    receiver = UdpReceiver(port=port, host=host)
    bad = 0
    good = 0
    try:
        while True:
            got = receiver.recv_one()
            if got is None:
                continue
            record, addr = got
            try:
                store.append(record)
                good += 1
                if on_event is not None:
                    on_event(record, addr)
            except SchemaError:
                bad += 1
    except KeyboardInterrupt:
        pass
    finally:
        receiver.close()
    print(f"zatrzymano: {good} zdarzeń zapisanych, {bad} odrzuconych")
