import unittest

from packet_lab import FIXTURES, ParseError, parse_frame


class PacketLabTest(unittest.TestCase):
    def test_udp_payload_excludes_ethernet_padding(self):
        p = parse_frame(FIXTURES["udp"])
        self.assertEqual(p["captured_bytes"], 60)
        self.assertEqual(p["ipv4"]["source"], "192.0.2.1")
        self.assertEqual(p["ipv4"]["destination"], "198.51.100.2")
        self.assertEqual(p["transport"]["length"], 12)
        self.assertEqual(p["transport"]["destination_port"], 8080)
        self.assertEqual(p["payload_hex"], "4c414221")
        self.assertEqual(p["unparsed_ethernet_tail_bytes"], 14)

    def test_tcp_ip_ihl_and_data_offset_use_words(self):
        p = parse_frame(FIXTURES["tcp"])
        self.assertEqual(p["captured_bytes"], 65)
        self.assertEqual(p["ipv4"]["header_bytes"], 24)
        self.assertEqual(p["transport"]["header_bytes"], 24)
        self.assertEqual(p["transport"]["destination_port"], 443)
        self.assertEqual(p["transport"]["sequence"], 1)
        self.assertEqual(p["transport"]["flags_low8_hex"], "18")
        self.assertEqual(p["payload_hex"], "4c4142")
        self.assertTrue(p["ipv4"]["dont_fragment"])

    def test_truncated_ethernet_header(self):
        with self.assertRaisesRegex(ParseError, "Ethernet II: truncated"):
            parse_frame(FIXTURES["udp"][:13])

    def test_truncated_ipv4_total_length(self):
        with self.assertRaisesRegex(ParseError, "IPv4 Total Length: truncated"):
            parse_frame(FIXTURES["udp"][:45])

    def test_unsupported_ethertype(self):
        frame = bytearray(FIXTURES["udp"])
        frame[12:14] = bytes.fromhex("86dd")
        with self.assertRaisesRegex(ParseError, "EtherType"):
            parse_frame(bytes(frame))

    def test_fragmentation_is_out_of_scope(self):
        frame = bytearray(FIXTURES["udp"])
        frame[20:22] = bytes.fromhex("2000")
        with self.assertRaisesRegex(ParseError, "fragmented datagrams"):
            parse_frame(bytes(frame))

    def test_bad_udp_length(self):
        frame = bytearray(FIXTURES["udp"])
        frame[38:40] = bytes.fromhex("000d")
        with self.assertRaisesRegex(ParseError, "UDP: length"):
            parse_frame(bytes(frame))

    def test_bad_tcp_offset(self):
        frame = bytearray(FIXTURES["tcp"])
        frame[50] = 0xF0
        with self.assertRaisesRegex(ParseError, "TCP header including options: truncated"):
            parse_frame(bytes(frame))


if __name__ == "__main__":
    unittest.main()
