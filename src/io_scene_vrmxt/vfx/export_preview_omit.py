# SPDX-License-Identifier: MIT
"""Unlink VFX preview helpers before stock VRM ``export_objects`` gather.

``pre_save_hook`` runs after gather. Viewport hide is not enough when
``export_invisibles`` is on. Unlink from collections for the duration of
``EXPORT_SCENE_OT_vrm.execute``.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Sequence
from typing import Any

from .geonodes_preview import is_preview_object

logger = logging.getLogger(__name__)

_EXECUTE_ATTR = "_vrmxt_original_execute"
_WRAPPED_FLAG = "_vrmxt_preview_omit"

try:
    import bpy
    from bpy.app.handlers import persistent
except ImportError:  # pragma: no cover - exercised only outside Blender
    bpy = None  # type: ignore[assignment]

    def persistent(f):  # type: ignore[no-redef, misc]
        return f


def iter_preview_objects(blend_data: Any) -> list[Any]:
    objects = getattr(blend_data, "objects", None)
    if objects is None:
        return []
    return [obj for obj in objects if is_preview_object(obj)]


def unlink_preview_objects(blend_data: Any) -> list[tuple[Any, list[Any]]]:
    """Unlink tagged preview objects. Return ``(object, collections)`` to restore."""
    stashed: list[tuple[Any, list[Any]]] = []
    for obj in iter_preview_objects(blend_data):
        collections = list(getattr(obj, "users_collection", ()) or ())
        for collection in collections:
            try:
                collection.objects.unlink(obj)
            except RuntimeError:
                logger.debug("Could not unlink preview object %r", obj, exc_info=True)
        stashed.append((obj, collections))
    return stashed


def relink_preview_objects(stashed: Sequence[tuple[Any, list[Any]]]) -> None:
    for obj, collections in stashed:
        for collection in collections:
            objects = getattr(collection, "objects", None)
            if objects is None:
                continue
            try:
                if obj.name in objects:
                    continue
            except (AttributeError, TypeError):
                pass
            try:
                objects.link(obj)
            except RuntimeError:
                logger.debug(
                    "Could not relink preview object %r",
                    obj,
                    exc_info=True,
                )


def _export_operator_type() -> Any | None:
    if bpy is None:
        return None
    return getattr(bpy.types, "EXPORT_SCENE_OT_vrm", None)


def _wrapped_execute(self: Any, context: Any) -> set[str]:
    original: Callable[..., set[str]] = getattr(type(self), _EXECUTE_ATTR)
    blend_data = getattr(context, "blend_data", None)
    stashed = unlink_preview_objects(blend_data) if blend_data is not None else []
    try:
        return original(self, context)
    finally:
        relink_preview_objects(stashed)


def wrap_vrm_export_operator() -> bool:
    """Patch ``EXPORT_SCENE_OT_vrm.execute`` if the stock operator is loaded."""
    cls = _export_operator_type()
    if cls is None:
        return False
    if getattr(cls.execute, _WRAPPED_FLAG, False):
        return True
    setattr(cls, _EXECUTE_ATTR, cls.execute)
    wrapped = _wrapped_execute
    setattr(wrapped, _WRAPPED_FLAG, True)
    cls.execute = wrapped  # type: ignore[method-assign]
    return True


def unwrap_vrm_export_operator() -> None:
    cls = _export_operator_type()
    if cls is None:
        return
    original = getattr(cls, _EXECUTE_ATTR, None)
    if original is None:
        return
    cls.execute = original  # type: ignore[method-assign]
    delattr(cls, _EXECUTE_ATTR)


def _retry_wrap() -> float | None:
    if wrap_vrm_export_operator():
        return None
    return 2.0


@persistent
def _on_load_post(_dummy: object) -> None:
    wrap_vrm_export_operator()


def register() -> None:
    if bpy is None:
        return
    wrap_vrm_export_operator()
    if _on_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load_post)
    if not wrap_vrm_export_operator():
        bpy.app.timers.register(_retry_wrap, first_interval=0.5)


def unregister() -> None:
    if bpy is None:
        return
    with contextlib.suppress(ValueError, AttributeError):
        bpy.app.timers.unregister(_retry_wrap)
    if _on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load_post)
    unwrap_vrm_export_operator()


__all__ = [
    "iter_preview_objects",
    "register",
    "relink_preview_objects",
    "unlink_preview_objects",
    "unregister",
    "wrap_vrm_export_operator",
]
