# SPDX-License-Identifier: MIT
"""Stock VRM 4.6.0 import JSON is MappingProxyType / tuple, not dict / list."""

from __future__ import annotations

import unittest
from collections.abc import Mapping
from types import MappingProxyType

from io_scene_vrmxt.common.constants import (
    EXTENSION_MATERIALS_OVERRIDE,
    EXTENSION_VRMXT_SPRITE_PARTICLE,
)
from io_scene_vrmxt.common.json_util import (
    as_dict,
    as_list,
    get_root_extension,
    to_plain_json,
)
from io_scene_vrmxt.format.vfx import parse_vfx


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(x) for x in value)
    return value


class TestJsonViewImport(unittest.TestCase):
    def test_as_dict_mapping_proxy(self) -> None:
        frozen = MappingProxyType({"a": 1})
        parsed = as_dict(frozen)
        self.assertEqual(parsed, {"a": 1})

    def test_as_list_tuple(self) -> None:
        self.assertEqual(as_list((1, 2)), [1, 2])

    def test_parse_vfx_from_json_view(self) -> None:
        raw = {
            "extensions": {
                EXTENSION_VRMXT_SPRITE_PARTICLE: {
                    "specVersion": "1.0",
                    "emitters": [{"node": 2, "name": "HookTestSpark"}],
                }
            },
            "nodes": [{}, {}, {}],
        }
        view = _freeze(raw)
        assert isinstance(view, Mapping)
        ext = get_root_extension(view, EXTENSION_VRMXT_SPRITE_PARTICLE)
        self.assertIsNotNone(ext)
        vfx = parse_vfx(ext, node_count=3)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        self.assertEqual(vfx.emitters[0].name, "HookTestSpark")

    def test_material_override_from_json_view(self) -> None:
        raw = {
            "materials": [
                {
                    "name": "Body",
                    "extensions": {
                        EXTENSION_MATERIALS_OVERRIDE: {
                            "specVersion": "1.0",
                            "overrides": [],
                        }
                    },
                }
            ]
        }
        view = _freeze(raw)
        materials = as_list(view["materials"])  # type: ignore[index]
        self.assertIsNotNone(materials)
        assert materials is not None
        entry = as_dict(materials[0])
        self.assertIsNotNone(entry)
        assert entry is not None
        extras = as_dict(entry.get("extensions"))
        self.assertIsNotNone(extras)
        assert extras is not None
        self.assertIn(EXTENSION_MATERIALS_OVERRIDE, extras)

    def test_to_plain_json_dumps(self) -> None:
        import json

        frozen = _freeze(
            {
                "overrides": [
                    {
                        "engine": "unity",
                        "material": {
                            "id": "VRMXT/HookTestToon",
                            "idType": "shaderName",
                        },
                    }
                ]
            }
        )
        dumped = json.dumps(to_plain_json(frozen))
        self.assertIn("VRMXT/HookTestToon", dumped)
