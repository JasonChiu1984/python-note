"""Synthetic read-only OPC UA lab; NoSecurity on IPv4 loopback only."""
import asyncio
from datetime import UTC, datetime
import sys

from asyncua import Client, Server, ua

URI = "urn:python-note:hvac:lab"
NODE = "Plant01.CHW01.LeavingTemperature"
URL = "opc.tcp://127.0.0.1:48531/python-note-hvac/"
END = object()


class Handler:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=8)
        self.dropped = 0

    def datachange_notification(self, node, value, data):
        # Keep callbacks short. Preserve status/timestamps, not only the value.
        dv = data.monitored_item.Value
        try:
            self.queue.put_nowait(dv)
        except asyncio.QueueFull:
            self.dropped += 1


async def main():
    server = Server()
    await server.init()
    server.set_endpoint(URL)  # fixed loopback; never widen for this lab
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    ns = await server.register_namespace(URI)
    plant = await server.nodes.objects.add_object(ns, "Plant01_CHW01")
    sensor = await plant.add_variable(ua.NodeId(NODE, ns), "LeavingTemperature", 7.0)
    # Default AccessLevel is read-only for external clients. Server still writes.
    async with server, Client(url=URL, timeout=5) as client:
        resolved = await client.get_namespace_index(URI)
        node = client.get_node(ua.NodeId(NODE, resolved))
        assert await node.read_value() == 7.0
        try:
            await node.write_value(99.0)
        except ua.UaStatusCodeError as error:
            assert error.code in (
                ua.StatusCodes.BadUserAccessDenied, ua.StatusCodes.BadNotWritable
            ), error
        else:
            raise AssertionError("the external client unexpectedly wrote a value")
        handler = Handler()
        sub = await client.create_subscription(100, handler)
        handle = await sub.subscribe_data_change(node, queuesize=4, sampling_interval=50)
        try:
            initial = await asyncio.wait_for(handler.queue.get(), timeout=5)
            assert initial.Value.Value == 7.0 and initial.StatusCode.is_good()
            source = datetime.now(UTC)
            dv = ua.DataValue(Value=ua.Variant(7.5, ua.VariantType.Double),
                              SourceTimestamp=source)
            await sensor.write_value(dv)
            changed = await asyncio.wait_for(handler.queue.get(), timeout=5)
            assert changed.Value.Value == 7.5
            assert changed.StatusCode.is_good()
            assert changed.SourceTimestamp == source
            assert not handler.dropped
            # Explicit app-queue overflow exercise. This is not server overflow.
            for _ in range(handler.queue.maxsize):
                handler.queue.put_nowait(END)
            # Exercise the same callback method without simulating protocol loss.
            from types import SimpleNamespace
            handler.datachange_notification(node, 7.5, SimpleNamespace(
                monitored_item=SimpleNamespace(Value=changed)))
            assert handler.dropped == 1
        finally:
            await sub.unsubscribe(handle)
            await sub.delete()
    print("PASS namespace lookup, read-only access, DataValue, subscription, app queue")


if __name__ == "__main__":
    if not __debug__:
        sys.exit("Run the checks without -O.")
    asyncio.run(main())
