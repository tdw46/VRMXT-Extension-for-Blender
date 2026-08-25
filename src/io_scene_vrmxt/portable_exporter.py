# SPDX-License-Identifier: MIT
"""Portable GLB/VRM JSON patching around a host VRM exporter.

This module intentionally does not copy or replace a VRM implementation. A
host first runs its installed VRM exporter, then this module atomically injects
VRMXT JSON into the resulting GLB while leaving the binary payload and stock
VRM extensions untouched.
"""

from __future__ import annotations

import json
import os
import struct
import tempfile
from collections.abc import Callable, Mapping, MutableMapping
from contextlib import suppress
from pathlib import Path
from typing import Any

GLB_MAGIC = b"glTF"
GLB_VERSION = 2
JSON_CHUNK_TYPE = 0x4E4F534A

JsonObject = MutableMapping[str, Any]
DocumentPatcher = Callable[[JsonObject, Mapping[str, int]], None]


def _read_glb(path: Path) -> tuple[JsonObject, list[tuple[int, bytes]]]:
    payload = path.read_bytes()
    if len(payload) < 20:
        raise ValueError("VRM file is too short to be a GLB")
    magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
    if magic != GLB_MAGIC or version != GLB_VERSION:
        raise ValueError("VRM file is not a glTF 2.0 binary")
    if declared_length != len(payload):
        raise ValueError("VRM GLB length does not match its header")

    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(payload):
        if offset + 8 > len(payload):
            raise ValueError("VRM GLB contains a truncated chunk header")
        chunk_length, chunk_type = struct.unpack_from("<II", payload, offset)
        offset += 8
        end = offset + chunk_length
        if end > len(payload):
            raise ValueError("VRM GLB contains a truncated chunk")
        chunks.append((chunk_type, payload[offset:end]))
        offset = end
    if not chunks or chunks[0][0] != JSON_CHUNK_TYPE:
        raise ValueError("VRM GLB does not begin with a JSON chunk")
    document = json.loads(chunks[0][1].decode("utf-8").rstrip(" \t\r\n\x00"))
    if not isinstance(document, dict):
        raise ValueError("VRM GLB JSON root must be an object")
    return document, chunks[1:]


def _encode_glb(
    document: Mapping[str, Any], trailing_chunks: list[tuple[int, bytes]]
) -> bytes:
    json_bytes = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    json_bytes += b" " * ((-len(json_bytes)) % 4)
    chunks = [(JSON_CHUNK_TYPE, json_bytes), *trailing_chunks]
    total_length = 12 + sum(8 + len(chunk) for _kind, chunk in chunks)
    output = bytearray(struct.pack("<4sII", GLB_MAGIC, GLB_VERSION, total_length))
    for chunk_type, chunk in chunks:
        if len(chunk) % 4:
            raise ValueError("Existing VRM GLB chunk is not four-byte aligned")
        output.extend(struct.pack("<II", len(chunk), chunk_type))
        output.extend(chunk)
    return bytes(output)


def material_name_to_index(document: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    materials = document.get("materials")
    if not isinstance(materials, list):
        return result
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            continue
        name = material.get("name")
        if isinstance(name, str) and name not in result:
            result[name] = index
    return result


def patch_exported_vrm(path: str | os.PathLike[str], patcher: DocumentPatcher) -> None:
    """Atomically patch an already-exported VRM using its stock material names."""

    target = Path(path)
    document, trailing_chunks = _read_glb(target)
    patcher(document, material_name_to_index(document))
    encoded = _encode_glb(document, trailing_chunks)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except Exception:
        with suppress(OSError):
            os.unlink(temporary_name)
        raise


__all__ = ["material_name_to_index", "patch_exported_vrm"]
