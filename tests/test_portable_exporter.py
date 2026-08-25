# SPDX-License-Identifier: MIT
"""Tests for host-independent VRM GLB patching."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from io_scene_vrmxt.portable_exporter import patch_exported_vrm


def _glb(document: dict, binary: bytes = b"\x00\x01\x02\x03") -> bytes:
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((-len(encoded)) % 4)
    chunks = [(0x4E4F534A, encoded), (0x004E4942, binary)]
    length = 12 + sum(8 + len(chunk) for _kind, chunk in chunks)
    result = bytearray(struct.pack("<4sII", b"glTF", 2, length))
    for kind, chunk in chunks:
        result.extend(struct.pack("<II", len(chunk), kind))
        result.extend(chunk)
    return bytes(result)


class TestPortableExporter(unittest.TestCase):
    def test_patch_preserves_binary_and_maps_material_names(self) -> None:
        document = {
            "asset": {"version": "2.0"},
            "materials": [{"name": "Face"}, {"name": "Mask"}],
        }
        binary = b"\x00\x01\x02\x03"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "avatar.vrm"
            path.write_bytes(_glb(document, binary))

            def patcher(payload, names):
                self.assertEqual(names, {"Face": 0, "Mask": 1})
                payload["extensionsUsed"] = ["VRMXT_materials_mtoonxt"]

            patch_exported_vrm(path, patcher)
            output = path.read_bytes()
        self.assertEqual(output[-len(binary) :], binary)
        _magic, _version, length = struct.unpack_from("<4sII", output, 0)
        self.assertEqual(length, len(output))
        json_length, json_kind = struct.unpack_from("<II", output, 12)
        self.assertEqual(json_kind, 0x4E4F534A)
        payload = json.loads(output[20 : 20 + json_length].decode("utf-8"))
        self.assertEqual(payload["extensionsUsed"], ["VRMXT_materials_mtoonxt"])

    def test_rejects_non_glb_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "avatar.vrm"
            path.write_bytes(b"not a glb")
            with self.assertRaises(ValueError):
                patch_exported_vrm(path, lambda _payload, _names: None)
            self.assertEqual(path.read_bytes(), b"not a glb")


if __name__ == "__main__":
    unittest.main()
