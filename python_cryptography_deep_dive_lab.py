"""本機 AES-GCM 教學：只處理合成資料，不寫入金鑰或連網。"""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
from secrets import token_bytes
import unittest

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VERSION = 1
NONCE_LEN = 12
TAG_LEN = 16
MAX_MESSAGE = 64 * 1024  # 本示例的應用限制，不是 GCM 規格上限。


class OpenError(ValueError):
    """拒絕未經驗證的資料。"""


@dataclass(frozen=True)
class Envelope:
    version: int
    kid: str
    nonce: bytes
    sealed: bytes  # PyCA 回傳 ciphertext || 16-byte tag。


def aad_for(version: int, kid: str, record_id: str) -> bytes:
    """只使用固定欄位與一致的 UTF-8 JSON 編碼；AAD 不保密。"""
    if not isinstance(record_id, str) or not 1 <= len(record_id) <= 128:
        raise ValueError("record_id 超出示例合約範圍")
    if not isinstance(kid, str) or not 1 <= len(kid) <= 64:
        raise ValueError("kid 超出示例合約範圍")
    return json.dumps([version, kid, record_id], ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def seal(key: bytes, kid: str, record_id: str, plaintext: bytes) -> Envelope:
    if len(plaintext) > MAX_MESSAGE:
        raise ValueError("明文太長")
    aad = aad_for(VERSION, kid, record_id)
    nonce = token_bytes(NONCE_LEN)  # 教具僅少量操作；正式服務需分配與用量政策。
    return Envelope(VERSION, kid, nonce, AESGCM(key).encrypt(nonce, plaintext, aad))


def open_record(keys: dict[str, bytes], envelope: Envelope, record_id: str) -> bytes:
    try:
        if type(envelope.version) is not int or envelope.version != VERSION:
            raise ValueError
        if not isinstance(envelope.nonce, bytes) or len(envelope.nonce) != NONCE_LEN:
            raise ValueError
        if not isinstance(envelope.sealed, bytes) or not TAG_LEN <= len(envelope.sealed) <= MAX_MESSAGE + TAG_LEN:
            raise ValueError
        aad = aad_for(envelope.version, envelope.kid, record_id)
        key = keys[envelope.kid]  # 固定映射；不根據外部 kid 拼接路徑。
        return AESGCM(key).decrypt(envelope.nonce, envelope.sealed, aad)
    except (InvalidTag, KeyError, TypeError, ValueError):
        raise OpenError("拒絕：格式、金鑰或驗證不符") from None


class TestAEAD(unittest.TestCase):
    def setUp(self):
        self.key = AESGCM.generate_key(bit_length=256)
        self.env = seal(self.key, "demo-v1", "record-1", b"HVAC demo")
        self.keys = {"demo-v1": self.key}

    def test_roundtrip(self):
        self.assertEqual(open_record(self.keys, self.env, "record-1"), b"HVAC demo")

    def test_wrong_aad(self):
        with self.assertRaises(OpenError):
            open_record(self.keys, self.env, "other-record")

    def test_modified_tag(self):
        v, kid, nonce, c = self.env.version, self.env.kid, self.env.nonce, self.env.sealed
        changed = Envelope(v, kid, nonce, c[:-1] + bytes([c[-1] ^ 1]))
        with self.assertRaises(OpenError):
            open_record(self.keys, changed, "record-1")

    def test_untrusted_key_id_and_version(self):
        for keys, env in ((self.keys, Envelope(2, self.env.kid, self.env.nonce, self.env.sealed)), ({}, self.env)):
            with self.assertRaises(OpenError):
                open_record(keys, env, "record-1")

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            seal(self.key, "demo-v1", "record-1", b"x" * (MAX_MESSAGE + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true")
    if parser.parse_args().test:
        unittest.main(argv=["lab"])
        return
    key = AESGCM.generate_key(bit_length=256)
    env = seal(key, "demo-v1", "record-1", b"HVAC demo")
    b64 = lambda data: base64.b64encode(data).decode("ascii")
    print(json.dumps({"v": env.version, "kid": env.kid, "nonce_b64": b64(env.nonce),
                      "sealed_b64": b64(env.sealed)}, ensure_ascii=False))
    print(open_record({env.kid: key}, env, "record-1").decode("ascii"))
    try:
        open_record({env.kid: key}, env, "wrong-record")
    except OpenError as exc:
        print(exc)


if __name__ == "__main__":
    main()
