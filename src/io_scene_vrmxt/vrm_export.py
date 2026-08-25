# SPDX-License-Identifier: MIT
"""VRM-host export orchestration owned entirely by the VRMXT extension."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .hooks import vrm1_hooks
from .mtoonxt.export_hook import apply_mtoonxt_export
from .mtoonxt.property_group import (
    relationships_from_scene,
    validate_relationships_in_scene,
)
from .mtoonxt.relationship_mapping import relationship_shorthand_extras
from .portable_exporter import _read_glb, material_name_to_index, patch_exported_vrm

logger = logging.getLogger(__name__)


@dataclass
class VrmxtExportResult:
    operator_result: set[str]
    material_count: int = 0
    patched: bool = False
    error: str = ""


def _export_hook_preferences(context: Any) -> Any | None:
    preferences = getattr(context, "preferences", None)
    addons = getattr(preferences, "addons", ()) if preferences is not None else ()
    for addon in tuple(addons):
        addon_preferences = getattr(addon, "preferences", None)
        if hasattr(addon_preferences, "enable_vrm1_export_extension_hooks"):
            return addon_preferences
    return None


class _ExportHookTransaction:
    """Enable all registered Extended VRM export hooks for one export."""

    def __init__(self, context: Any):
        self._preferences = None
        self._previous = None
        vrm1_hooks.register()
        if not vrm1_hooks.hooks_available():
            return
        preferences = _export_hook_preferences(context)
        if preferences is None:
            return
        self._preferences = preferences
        self._previous = bool(
            getattr(preferences, "enable_vrm1_export_extension_hooks", False)
        )
        preferences.enable_vrm1_export_extension_hooks = True

    def close(self) -> None:
        if self._preferences is None or self._previous is None:
            return
        try:
            self._preferences.enable_vrm1_export_extension_hooks = self._previous
        except (AttributeError, ReferenceError, RuntimeError):
            logger.debug("Unable to restore VRM export-hook preference", exc_info=True)
        self._preferences = None
        self._previous = None


def _invoke_host_export(export_operator: Any, filepath: str) -> set[str]:
    properties = None
    get_rna_type = getattr(export_operator, "get_rna_type", None)
    if callable(get_rna_type):
        try:
            properties = get_rna_type().properties
        except (AttributeError, RuntimeError, TypeError):
            properties = None
    keywords: dict[str, Any] = {"filepath": filepath}
    if properties is not None and "use_addon_preferences" in properties:
        keywords["use_addon_preferences"] = True
    return set(export_operator("EXEC_DEFAULT", **keywords))


def _document_vrmxt_signature(document: dict[str, Any]) -> tuple[Any, tuple[Any, ...]]:
    root_extension = copy.deepcopy(
        (document.get("extensions") or {}).get("VRMXT_materials_mtoonxt")
        if isinstance(document.get("extensions"), dict)
        else None
    )
    material_extensions = []
    for material in document.get("materials", ()) or ():
        extensions = material.get("extensions") if isinstance(material, dict) else None
        material_extensions.append(
            copy.deepcopy(extensions.get("VRMXT_materials_mtoonxt"))
            if isinstance(extensions, dict)
            else None
        )
    return root_extension, tuple(material_extensions)


def _apply_current_scene(document: dict[str, Any], scene: Any) -> None:
    apply_mtoonxt_export(
        SimpleNamespace(
            json_dict=document,
            material_name_to_index=material_name_to_index(document),
            scene=scene,
        )
    )


def _count_vrmxt_materials(document: dict[str, Any]) -> int:
    indices: set[int] = set()
    for index, material in enumerate(document.get("materials", ()) or ()):
        extensions = material.get("extensions") if isinstance(material, dict) else None
        if isinstance(extensions, dict) and "VRMXT_materials_mtoonxt" in extensions:
            indices.add(index)
    root = document.get("extensions")
    extension = root.get("VRMXT_materials_mtoonxt") if isinstance(root, dict) else None
    relationships = (
        extension.get("stencilRelationships") if isinstance(extension, dict) else None
    )
    if isinstance(relationships, list):
        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue
            for key in ("writers", "readers"):
                for index in relationship.get(key, ()) or ():
                    if isinstance(index, int):
                        indices.add(index)
    return len(indices)


def validate_scene_stencil_relationships(scene: Any) -> list[str]:
    property_errors = validate_relationships_in_scene(scene)
    if property_errors:
        return property_errors
    try:
        import bpy
    except ImportError:
        return []
    name_to_index = {
        str(material.name): index for index, material in enumerate(bpy.data.materials)
    }
    relationships = relationships_from_scene(name_to_index, scene=scene)
    _extras, errors = relationship_shorthand_extras(
        relationships,
        material_count=len(name_to_index),
    )
    return errors


def export_vrm_with_vrmxt(
    filepath: str,
    *,
    context: Any | None = None,
) -> VrmxtExportResult:
    """Export through the installed VRM add-on, then ensure VRMXT JSON exists.

    The host VRM exporter remains authoritative for every stock VRM/glTF
    feature. VRMXT only contributes its registered extension JSON, using the
    Extended VRM hook when available and an atomic JSON-chunk patch otherwise.
    """

    try:
        import bpy
    except ImportError:
        return VrmxtExportResult({"CANCELLED"}, error="Blender is unavailable.")
    context = context or bpy.context
    scene = getattr(context, "scene", None)
    errors = validate_scene_stencil_relationships(scene)
    if errors:
        return VrmxtExportResult({"CANCELLED"}, error=errors[0])
    export_operator = getattr(bpy.ops.export_scene, "vrm", None)
    if export_operator is None:
        return VrmxtExportResult(
            {"CANCELLED"}, error="The VRM add-on export operator is unavailable."
        )

    transaction = _ExportHookTransaction(context)
    try:
        operator_result = _invoke_host_export(export_operator, filepath)
    finally:
        transaction.close()
    if "FINISHED" not in operator_result:
        return VrmxtExportResult(operator_result)

    target = Path(filepath)
    try:
        document, _chunks = _read_glb(target)
        expected = copy.deepcopy(document)
        _apply_current_scene(expected, scene)
        patched = _document_vrmxt_signature(document) != _document_vrmxt_signature(
            expected
        )
        if patched:
            patch_exported_vrm(
                target,
                lambda payload, _material_names: _apply_current_scene(payload, scene),
            )
            document, _chunks = _read_glb(target)
    except Exception as error:  # noqa: BLE001 - preserve the completed stock VRM
        return VrmxtExportResult(
            {"CANCELLED"},
            error=(
                f"The VRM was exported, but VRMXT metadata could not be added: {error}"
            ),
        )

    count = _count_vrmxt_materials(document)
    authored = bool(
        getattr(
            getattr(scene, "vrmxt_mtoonxt_relationship_settings", None),
            "relationships",
            (),
        )
    )
    if authored and count == 0:
        return VrmxtExportResult(
            {"CANCELLED"},
            error=(
                "No VRMXT stencil metadata was written. "
                "VRMXT requires VRM 1.0 MToon materials."
            ),
        )
    return VrmxtExportResult(operator_result, material_count=count, patched=patched)


__all__ = [
    "VrmxtExportResult",
    "export_vrm_with_vrmxt",
    "validate_scene_stencil_relationships",
]
