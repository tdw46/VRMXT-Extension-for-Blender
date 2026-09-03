# SPDX-License-Identifier: MIT
"""Tests for unlinking VFX preview objects around stock VRM export."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from io_scene_vrmxt.vfx.export_preview_omit import (
    relink_preview_objects,
    unlink_preview_objects,
)
from io_scene_vrmxt.vfx.geonodes_preview import PREVIEW_CUSTOM_PROP


class _Collection:
    def __init__(self) -> None:
        self.objects = _ObjectCollection()


class _ObjectCollection:
    def __init__(self) -> None:
        self._items: list[object] = []

    def link(self, obj: object) -> None:
        self._items.append(obj)

    def unlink(self, obj: object) -> None:
        self._items.remove(obj)

    def __contains__(self, name: str) -> bool:
        return any(getattr(item, "name", None) == name for item in self._items)


class TestUnlinkPreviewObjects(unittest.TestCase):
    def test_unlinks_tagged_and_relinks(self) -> None:
        collection = _Collection()
        preview = SimpleNamespace(
            name="VRMXT_sprite_x.000",
            users_collection=[collection],
            get=lambda key, default=None: 1 if key == PREVIEW_CUSTOM_PROP else default,
        )
        mesh = SimpleNamespace(
            name="Body",
            users_collection=[collection],
            get=lambda key, default=None: default,
        )
        collection.objects.link(preview)
        collection.objects.link(mesh)
        blend_data = SimpleNamespace(objects=[preview, mesh])

        stashed = unlink_preview_objects(blend_data)
        self.assertEqual(len(stashed), 1)
        self.assertNotIn(preview, collection.objects._items)
        self.assertIn(mesh, collection.objects._items)

        relink_preview_objects(stashed)
        self.assertIn(preview, collection.objects._items)


if __name__ == "__main__":
    unittest.main()
