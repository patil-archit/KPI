"""Minimal Modbus/TCP server exposing PLC-1 (unit 1) and the SIS (unit 2).

Written by hand rather than with a library so that every request goes through
the plant's access-control and evidence path with the client's real IP.
Supported function codes: 1, 2, 3, 4, 5, 6, 15, 16.
"""
import asyncio
import struct

from ..events import emit
from .sim import plant

ILLEGAL_FUNCTION, ILLEGAL_ADDRESS, ILLEGAL_VALUE, DEVICE_FAILURE = 1, 2, 3, 4


def _exc(fc: int, code: int) -> bytes:
    return bytes([fc | 0x80, code])


def _pack_bits(bits: list[int]) -> bytes:
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def handle_pdu(unit: int, pdu: bytes, ip: str) -> bytes:
    if not pdu:
        return _exc(0, ILLEGAL_FUNCTION)
    fc = pdu[0]
    if unit not in (1, 2):
        return _exc(fc, ILLEGAL_ADDRESS)
    ctx = {"src_ip": ip, "protocol": "modbus/tcp", "function_code": fc, "actor": None}
    try:
        if fc in (1, 2, 3, 4):
            addr, count = struct.unpack(">HH", pdu[1:5])
            if not 1 <= count <= 125:
                return _exc(fc, ILLEGAL_VALUE)
            table = {1: "coil", 2: "coil", 3: "hr", 4: "ir"}[fc]
            vals = plant.read(unit, table, addr, count, ctx)
            if vals is None:
                return _exc(fc, DEVICE_FAILURE)
            if fc in (1, 2):
                data = _pack_bits(vals)
                return bytes([fc, len(data)]) + data
            return bytes([fc, count * 2]) + b"".join(struct.pack(">H", v) for v in vals)
        if fc == 5:
            addr, raw = struct.unpack(">HH", pdu[1:5])
            if raw not in (0x0000, 0xFF00):
                return _exc(fc, ILLEGAL_VALUE)
            ok, _ = plant.write(unit, "coil", addr, [1 if raw == 0xFF00 else 0], ctx)
            return pdu[:5] if ok else _exc(fc, ILLEGAL_ADDRESS)
        if fc == 6:
            addr, raw = struct.unpack(">HH", pdu[1:5])
            ok, _ = plant.write(unit, "hr", addr, [raw], ctx)
            return pdu[:5] if ok else _exc(fc, ILLEGAL_VALUE)
        if fc == 15:
            addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
            data = pdu[6:6 + nbytes]
            bits = [(data[i // 8] >> (i % 8)) & 1 for i in range(count)]
            ok, _ = plant.write(unit, "coil", addr, bits, ctx)
            return struct.pack(">BHH", fc, addr, count) if ok else _exc(fc, ILLEGAL_ADDRESS)
        if fc == 16:
            addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
            regs = list(struct.unpack(">" + "H" * count, pdu[6:6 + nbytes]))
            ok, _ = plant.write(unit, "hr", addr, regs, ctx)
            return struct.pack(">BHH", fc, addr, count) if ok else _exc(fc, ILLEGAL_VALUE)
    except struct.error:
        return _exc(fc, ILLEGAL_VALUE)
    return _exc(fc, ILLEGAL_FUNCTION)


async def _client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    ip = peer[0] if peer else "unknown"
    if ip.startswith("::ffff:"):
        ip = ip[7:]
    emit(source="network", host="plc-01", event_type="tcp_session_open", protocol="modbus/tcp",
         src_ip=ip, outcome="info", dst_port=502)
    try:
        while True:
            header = await reader.readexactly(7)
            tid, pid, length, unit = struct.unpack(">HHHB", header)
            if pid != 0 or length < 2 or length > 260:
                break
            pdu = await reader.readexactly(length - 1)
            resp = await asyncio.to_thread(handle_pdu, unit, pdu, ip)
            writer.write(struct.pack(">HHHB", tid, 0, len(resp) + 1, unit) + resp)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        writer.close()


async def serve(host: str, port: int) -> None:
    server = await asyncio.start_server(_client, host, port)
    async with server:
        await server.serve_forever()
