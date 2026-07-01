from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Iterable


class RustDeskLiveStatusError(RuntimeError):
    pass


@dataclass(slots=True)
class LiveStatusResult:
    online: dict[str, bool]
    response_states_hex: str
    requested: int


def query_hbbs_online_status(
    host: str,
    port: int,
    peer_ids: Iterable[str],
    *,
    requester_id: str = "rustdesk-addressbook",
    timeout: float = 3.0,
) -> LiveStatusResult:
    """Query hbbs with RustDesk's experimental OnlineRequest protocol.

    This is intentionally implemented without generated protobuf code to keep
    the Docker image small. It implements only the tiny subset we need:
    RendezvousMessage.online_request -> OnlineRequest{id, peers[]}
    RendezvousMessage.online_response -> OnlineResponse{states}

    RustDesk uses hbb_common::bytes_codec framing on TCP. OnlineRequest is handled by hbbs on the extra TCP listener (default 21115 when the main hbbs port is 21116). This function uses
    the same variable-length frame header and then sends a protobuf payload.
    """
    ids = [str(x).strip() for x in peer_ids if str(x).strip()]
    if not ids:
        return LiveStatusResult(online={}, response_states_hex="", requested=0)
    if not host.strip():
        raise RustDeskLiveStatusError("hbbs Host fehlt.")
    if port < 1 or port > 65535:
        raise RustDeskLiveStatusError("hbbs Port ist ungültig.")

    payload = _build_online_request(ids, requester_id=requester_id)
    frame = _encode_frame(payload)

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(frame)
            response_payload = _read_frame(sock)
    except socket.timeout as exc:
        raise RustDeskLiveStatusError(
            "Timeout bei der hbbs Live-Abfrage. Prüfe Host, Port und Firewall. Für OnlineRequest ist normalerweise TCP 21115 nötig, wenn dein hbbs-Hauptport 21116 ist."
        ) from exc
    except OSError as exc:
        raise RustDeskLiveStatusError(f"hbbs Verbindung fehlgeschlagen: {exc}") from exc

    states = _extract_online_response_states(response_payload)
    if states is None:
        raise RustDeskLiveStatusError(
            "hbbs hat geantwortet, aber keine OnlineResponse geliefert. "
            "Die Serverversion unterstützt diese Abfrage eventuell nicht oder erwartet ein anderes Protokoll."
        )

    online: dict[str, bool] = {}
    for i, peer_id in enumerate(ids):
        state_byte = states[i // 8] if i // 8 < len(states) else 0
        bit_idx = 7 - (i % 8)
        online[peer_id] = bool(state_byte & (1 << bit_idx))

    return LiveStatusResult(online=online, response_states_hex=states.hex(), requested=len(ids))


def _build_online_request(peer_ids: list[str], *, requester_id: str) -> bytes:
    inner = bytearray()
    requester_id = requester_id.strip()
    if requester_id:
        inner += _pb_string(1, requester_id)
    for peer_id in peer_ids:
        inner += _pb_string(2, peer_id)
    # RendezvousMessage.online_request = 23
    return _pb_key(23, 2) + _pb_varint(len(inner)) + bytes(inner)


def _extract_online_response_states(payload: bytes) -> bytes | None:
    # Top-level: RendezvousMessage.online_response = 24, length-delimited.
    for field_no, wire_type, value in _pb_iter_fields(payload):
        if field_no == 24 and wire_type == 2 and isinstance(value, bytes):
            for inner_no, inner_wire, inner_value in _pb_iter_fields(value):
                if inner_no == 1 and inner_wire == 2 and isinstance(inner_value, bytes):
                    return inner_value
    return None


def _pb_string(field_no: int, value: str) -> bytes:
    data = value.encode("utf-8")
    return _pb_key(field_no, 2) + _pb_varint(len(data)) + data


def _pb_key(field_no: int, wire_type: int) -> bytes:
    return _pb_varint((field_no << 3) | wire_type)


def _pb_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint must be positive")
    out = bytearray()
    while True:
        to_write = value & 0x7F
        value >>= 7
        if value:
            out.append(to_write | 0x80)
        else:
            out.append(to_write)
            return bytes(out)


def _pb_read_varint(data: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    result = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7
        if shift > 63:
            raise RustDeskLiveStatusError("Ungültiges Protobuf-Varint in hbbs Antwort.")
    raise RustDeskLiveStatusError("Unvollständiges Protobuf-Varint in hbbs Antwort.")


def _pb_iter_fields(data: bytes):
    pos = 0
    while pos < len(data):
        key, pos = _pb_read_varint(data, pos)
        field_no = key >> 3
        wire_type = key & 0x07
        if wire_type == 0:
            value, pos = _pb_read_varint(data, pos)
            yield field_no, wire_type, value
        elif wire_type == 1:
            if pos + 8 > len(data):
                raise RustDeskLiveStatusError("Unvollständiges 64-bit Feld in hbbs Antwort.")
            yield field_no, wire_type, data[pos : pos + 8]
            pos += 8
        elif wire_type == 2:
            length, pos = _pb_read_varint(data, pos)
            if pos + length > len(data):
                raise RustDeskLiveStatusError("Unvollständiges length-delimited Feld in hbbs Antwort.")
            yield field_no, wire_type, data[pos : pos + length]
            pos += length
        elif wire_type == 5:
            if pos + 4 > len(data):
                raise RustDeskLiveStatusError("Unvollständiges 32-bit Feld in hbbs Antwort.")
            yield field_no, wire_type, data[pos : pos + 4]
            pos += 4
        else:
            raise RustDeskLiveStatusError(f"Nicht unterstützter Protobuf wire type: {wire_type}")


def _encode_frame(payload: bytes) -> bytes:
    n = len(payload)
    if n <= 0x3F:
        return bytes([(n << 2) & 0xFF]) + payload
    if n <= 0x3FFF:
        header = ((n << 2) | 0x1).to_bytes(2, "little")
        return header + payload
    if n <= 0x3FFFFF:
        h = (n << 2) | 0x2
        return h.to_bytes(3, "little") + payload
    if n <= 0x3FFFFFFF:
        header = ((n << 2) | 0x3).to_bytes(4, "little")
        return header + payload
    raise RustDeskLiveStatusError("OnlineRequest ist zu groß.")


def _read_frame(sock: socket.socket) -> bytes:
    first = _recv_exact(sock, 1)[0]
    head_len = (first & 0x03) + 1
    header = bytes([first])
    if head_len > 1:
        header += _recv_exact(sock, head_len - 1)
    n = int.from_bytes(header, "little") >> 2
    if n > 10 * 1024 * 1024:
        raise RustDeskLiveStatusError("hbbs Antwort ist unerwartet groß.")
    return _recv_exact(sock, n)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < n:
        chunk = sock.recv(n - len(chunks))
        if not chunk:
            raise RustDeskLiveStatusError("hbbs hat die Verbindung geschlossen, bevor eine vollständige Antwort kam. Häufige Ursache: falscher Port. OnlineRequest läuft bei RustDesk normalerweise auf dem NAT-Test/Online-Port TCP 21115, nicht auf dem Hauptport 21116.")
        chunks.extend(chunk)
    return bytes(chunks)
