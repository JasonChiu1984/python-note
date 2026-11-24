"""Opt-in read-only SDK examples for an authorized lab. See README.md."""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
import json
from queue import Empty, Full, Queue

from protocol_lab import (
    FIELDBUS_FIXTURES, bacnet_read, fieldbus_ua_frame, modbus_float,
    mqtt_read, opcua_quality, temperature, zigbee_read,
)


def read_modbus(args):
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient

    if args.serial:
        client = ModbusSerialClient(
            args.target, baudrate=args.baudrate, parity=args.parity,
            stopbits=args.stopbits, bytesize=8, timeout=3, retries=0,
        )
    else:
        client = ModbusTcpClient(args.target, port=args.port, timeout=3, retries=0)
    try:
        if not client.connect():
            raise ConnectionError("Modbus connection failed")
        response = client.read_holding_registers(args.offset, count=2, device_id=args.unit)
        if response.isError():
            raise RuntimeError(str(response))
        value = modbus_float(response.registers, low_word_first=args.low_word_first)
        return asdict(temperature(f"modbus:{args.unit}/holding/{args.offset}", value))
    finally:
        client.close()


async def read_bacnet(args):
    import BAC0

    async with asyncio.timeout(12):
        options = {"ip": args.bind, "deviceId": args.local_device_id}
        if args.bbmd:
            options.update(bbmdAddress=args.bbmd, bbmdTTL=args.bbmd_ttl)
        async with BAC0.start(**options) as bacnet:
            request = f"{args.target} analogInput {args.instance}"
            value = await bacnet.read(f"{request} presentValue")
            units = await bacnet.read(f"{request} units")
            flags = await bacnet.read(f"{request} statusFlags")
            reading = bacnet_read(f"bacnet:{args.target}/analogInput/{args.instance}", value, units, list(flags))
            return {**asdict(reading), "units": str(units), "status_flags": list(flags)}


def ua_sample(args, data):
    value = data.Value.Value if data.Value is not None else None
    quality = opcua_quality(data.StatusCode.value)
    if args.fieldbus:
        reading = fieldbus_ua_frame(args.fieldbus, args.point, value, quality)
    else:
        reading = temperature(f"opcua:{args.namespace_uri}/{args.point}", value, quality)
    return {**asdict(reading), "status": str(data.StatusCode), "source_timestamp": data.SourceTimestamp}


async def watch_opcua(client, node, args):
    updates = asyncio.Queue(maxsize=min(args.watch, 32))

    class Handler:
        def datachange_notification(self, node, value, data):
            if not updates.full():
                updates.put_nowait(data.monitored_item.Value)

    subscription = await client.create_subscription(500, Handler())
    try:
        await subscription.subscribe_data_change(node)
        for _ in range(args.watch):
            print_result(ua_sample(args, await updates.get()))
    finally:
        await subscription.delete()


async def read_opcua(args):
    from asyncua import Client, ua
    from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256

    async with asyncio.timeout(args.timeout):
        async with secured_ua_client(Client(args.endpoint, timeout=4), args, ua, SecurityPolicyBasic256Sha256) as client:
            namespace = await client.get_namespace_index(args.namespace_uri)
            node = client.get_node(ua.NodeId(args.point, namespace))
            if args.watch:
                await watch_opcua(client, node, args)
                return None
            return ua_sample(args, await node.read_data_value(raise_on_bad_status=False))


@asynccontextmanager
async def secured_ua_client(client, args, ua, policy):
    if args.certificate is not None:
        await client.set_security(
            policy, args.certificate, args.private_key, server_certificate=args.server_certificate,
            mode=ua.MessageSecurityMode.SignAndEncrypt,
        )
    async with client:
        yield client


def read_broker(args):
    import paho.mqtt.client as mqtt

    # Keep a small handoff so callback processing cannot create an unbounded backlog.
    events = Queue(maxsize=1)

    def offer(event):
        try:
            events.put_nowait(event)
        except Full:
            pass  # A sample or error is already waiting for the one-shot reader.

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            offer(ConnectionError(f"Broker refused connection: {reason_code}"))
            return
        client.subscribe(args.topic, qos=1)

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            offer(PermissionError(f"Broker refused subscription: {reason_codes}"))

    def on_message(client, userdata, message):
        if message.topic != args.topic or message.retain:
            return
        if args.protocol == "zigbee":
            try:
                state = json.loads(message.payload)
            except (UnicodeError, ValueError):
                return
            if not isinstance(state, dict) or "temperature" not in state:
                return
        offer(message.payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    if not args.loopback_plaintext:
        client.tls_set(ca_certs=args.ca)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=30)
    client.loop_start()
    try:
        try:
            payload = events.get(timeout=args.wait)
        except Empty as exc:
            raise TimeoutError("No matching non-retained reading before the deadline") from exc
        if isinstance(payload, Exception):
            raise payload
        adapter = zigbee_read if args.protocol == "zigbee" else mqtt_read
        return asdict(adapter(args.topic, payload))
    finally:
        client.disconnect()
        client.loop_stop()


def print_result(value):
    print(json.dumps(value, ensure_ascii=False, default=str, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="protocol", required=True)
    modbus = subs.add_parser("modbus")
    modbus.add_argument("target", help="TCP host or serial device path")
    modbus.add_argument("--port", type=int, default=502)
    modbus.add_argument("--serial", action="store_true")
    modbus.add_argument("--baudrate", type=int, default=9600)
    modbus.add_argument("--parity", choices=["N", "E", "O"], default="E")
    modbus.add_argument("--stopbits", type=int, choices=[1, 2], default=1)
    modbus.add_argument("--unit", type=int, required=True)
    modbus.add_argument("--offset", type=int, default=0)
    modbus.add_argument("--low-word-first", action="store_true")

    bacnet = subs.add_parser("bacnet")
    bacnet.add_argument("target")
    bacnet.add_argument("--bind", required=True, help="local lab IPv4/prefix")
    bacnet.add_argument("--instance", type=int, required=True)
    bacnet.add_argument("--local-device-id", type=int, default=420100)
    bacnet.add_argument("--bbmd", help="BBMD IPv4 address and optional UDP port")
    bacnet.add_argument("--bbmd-ttl", type=int, default=300)

    opcua = subs.add_parser("opcua")
    opcua.add_argument("endpoint")
    opcua.add_argument("namespace_uri")
    opcua.add_argument("point", help="string identifier in that namespace")
    opcua.add_argument("--certificate")
    opcua.add_argument("--private-key")
    opcua.add_argument("--server-certificate")
    opcua.add_argument("--fieldbus", choices=FIELDBUS_FIXTURES, help="decode a PLC snapshot value")
    opcua.add_argument("--watch", type=int, default=0, help="number of subscription samples to print")
    opcua.add_argument("--timeout", type=float, default=12, help="total time limit in seconds")

    for name in ("mqtt", "zigbee"):
        broker = subs.add_parser(name)
        broker.add_argument("host")
        broker.add_argument("topic", help="one exact topic to read")
        broker.add_argument("--port", type=int)
        broker.add_argument("--ca")
        broker.add_argument("--loopback-plaintext", action="store_true")
        broker.add_argument("--wait", type=float, default=15, help="seconds to wait for a reading")

    args = parser.parse_args()
    if args.protocol == "modbus":
        value = read_modbus(args)
    elif args.protocol == "bacnet":
        value = asyncio.run(read_bacnet(args))
    elif args.protocol == "opcua":
        certs = (args.certificate, args.private_key, args.server_certificate)
        if any(certs) and not all(certs):
            parser.error("Provide --certificate, --private-key, and --server-certificate together")
        if args.watch < 0 or not 0 < args.timeout <= 3600:
            parser.error("--watch must be nonnegative and --timeout must be between 0 and 3600 seconds")
        value = asyncio.run(read_opcua(args))
    else:
        if not 0 < args.wait <= 3600:
            parser.error("--wait must be between 0 and 3600 seconds")
        if args.loopback_plaintext and args.host.lower() not in {"127.0.0.1", "::1", "localhost"}:
            parser.error("--loopback-plaintext requires a loopback host")
        if "+" in args.topic or "#" in args.topic:
            parser.error("Provide a single exact topic")
        if args.port is None:
            args.port = 1883 if args.loopback_plaintext else 8883
        value = read_broker(args)
    if value is not None:
        print_result(value)


if __name__ == "__main__":
    main()
