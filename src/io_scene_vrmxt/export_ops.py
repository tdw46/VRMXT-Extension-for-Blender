# SPDX-License-Identifier: MIT
"""Standalone VRMXT export operator around the installed VRM add-on."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from .vrm_export import export_vrm_with_vrmxt

try:
    import bpy
    from bpy.props import StringProperty
    from bpy.types import Context, Operator
    from bpy_extras.io_utils import ExportHelper
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Operator = object  # type: ignore[misc, assignment]
    ExportHelper = object  # type: ignore[misc, assignment]


if bpy is not None:

    class VRMXT_OT_export_vrm(Operator, ExportHelper):
        bl_idname = "vrmxt.export_vrm"
        bl_label = "Export VRM with VRMXT"
        bl_description = (
            "Export through the installed VRM add-on and add authored VRMXT extensions"
        )
        bl_options: ClassVar[set[str]] = {"REGISTER"}

        filename_ext = ".vrm"
        filter_glob: StringProperty(default="*.vrm", options={"HIDDEN"})

        def execute(self, context: Context) -> set[str]:
            result = export_vrm_with_vrmxt(self.filepath, context=context)
            if result.error:
                self.report({"ERROR"}, result.error)
            elif "FINISHED" in result.operator_result:
                self.report(
                    {"INFO"},
                    "Exported VRM with VRMXT metadata on "
                    f"{result.material_count} material(s).",
                )
            return result.operator_result

    CLASSES = (VRMXT_OT_export_vrm,)
else:  # pragma: no cover
    CLASSES = ()


def _draw_export_menu(self: object, _context: object) -> None:
    self.layout.operator(
        "vrmxt.export_vrm",
        text="VRM with VRMXT Extensions (.vrm)",
    )


def register() -> None:
    if bpy is None:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(_draw_export_menu)


def unregister() -> None:
    if bpy is None:
        return
    with contextlib.suppress(AttributeError, RuntimeError, ValueError):
        bpy.types.TOPBAR_MT_file_export.remove(_draw_export_menu)
    for cls in reversed(CLASSES):
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)


__all__ = ["register", "unregister"]
