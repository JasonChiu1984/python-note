import unittest

from release_note_lab import message


class MessageTest(unittest.TestCase):
    def test_packaged_resource(self):
        self.assertEqual(message(), "Release artifact verified")
