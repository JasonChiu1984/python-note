"""Run a local AHU01 teaching endpoint for Modbus TCP, BACnet/IP or OPC UA."""

import argparse
import asyncio
from datetime import datetime, timezone
from itertools import cycle
import struct


def modbus_response(unit: int, pdu: bytes) -> bytes:
    function = pdu[0]
    if unit != 7:
        return bytes([function | 0x80, 0x0B])
    if function != 3:
        return bytes([function | 0x80, 0x01])
    if len(pdu) != 5:
        return bytes([0x83, 0x03])
    address, count = struct.unpack(">HH", pdu[1:])
    if (address, count) != (0, 2):
        return bytes([0x83, 0x02])
    return struct.pack(">BBf", 3, 4, 22.0)


async def modbus_exchange(reader, writer):
    try:
        async with asyncio.timeout(5):
            while True:
                header = await reader.readexactly(7)
                transaction, protocol, length, unit = struct.unpack(">HHHB", header)
                if protocol != 0 or not 2 <= length <= 254:
                    break
                pdu = await reader.readexactly(length - 1)
                reply = modbus_response(unit, pdu)
                writer.write(struct.pack(">HHHB", transaction, 0, len(reply) + 1, unit) + reply)
                await writer.drain()
    except (asyncio.IncompleteReadError, TimeoutError, ConnectionError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def modbus_server(port):
    listener = await asyncio.start_server(modbus_exchange, "127.0.0.1", port)
    async with listener:
        print(f"Modbus TCP 127.0.0.1:{port}, Unit 7, FC03, offset 0", flush=True)
        await listener.serve_forever()


async def bacnet_server(bind, port):
    import BAC0
    from BAC0.core.devices.local.factory import analog_input

    async with BAC0.start(ip=bind, port=port, deviceId=420101) as server:
        point = analog_input(
            name="AHU01.SAT", instance=1, presentValue=22.0,
            properties={"units": "degreesCelsius"},
        )
        point.add_objects_to_application(server)
        print(f"BACnet/IP {bind} UDP {port}, Device 420101, analogInput:1", flush=True)
        await asyncio.Event().wait()


async def opcua_server(port):
    from asyncua import Server, ua

    server = Server()
    await server.init()
    endpoint = f"opc.tcp://127.0.0.1:{port}/lab/"
    server.set_endpoint(endpoint)
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    ns = await server.register_namespace("urn:example:plant")
    ahu = await server.nodes.objects.add_object(ns, "AHU01")
    point = await ahu.add_variable(ua.NodeId("AHU01.SAT", ns), "SAT", 22.0)
    snapshots = []
    for bus in ("PROFINET", "PROFIBUS", "CCLink"):
        node_id = ua.NodeId(f"AHU01.{bus}.Snapshot", ns)
        node = await ahu.add_variable(node_id, f"{bus}Snapshot", bytes.fromhex("01 00 DC"))
        snapshots.append(node)

    async with server:
        print(f"OPC UA {endpoint}, urn:example:plant", flush=True)
        for value in cycle((22.0, 22.5, -5.0, None)):
            now = datetime.now(timezone.utc)
            status = ua.StatusCodes.Good if value is not None else ua.StatusCodes.BadNoData
            await point.write_value(ua.DataValue(
                ua.Variant(value, ua.VariantType.Double if value is not None else ua.VariantType.Null),
                ua.StatusCode(status), SourceTimestamp=now,
            ))
            valid = value is not None
            packed = struct.pack(">Bh", int(valid), round(value * 10) if valid else 0)
            for snapshot in snapshots:
                await snapshot.write_value(ua.DataValue(
                    ua.Variant(packed, ua.VariantType.ByteString), SourceTimestamp=now,
                ))
            await asyncio.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", choices=["modbus", "bacnet", "opcua"])
    parser.add_argument("--port", type=int)
    parser.add_argument("--bind", default="127.0.0.1/32", help="BACnet/IP local test interface")
    args = parser.parse_args()

    if args.protocol == "modbus":
        serve = modbus_server(args.port or 15020)
    elif args.protocol == "bacnet":
        serve = bacnet_server(args.bind, args.port or 47809)
    else:
        serve = opcua_server(args.port or 4840)
    try:
        asyncio.run(serve)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
