# SPDX-License-Identifier: MIT
"""Stable integration surface for standalone and embedded hosts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from .format.mtoonxt import VrmxtMaterialsMtoonxt
from .hooks import vrm1_hooks
from .mtoonxt.export_hook import (
    register_external_export_provider,
    unregister_external_export_provider,
)

MtoonxtExportProvider = Callable[
    [Any, dict[str, int], int], Optional[VrmxtMaterialsMtoonxt]
]
_EMBEDDED_PROVIDER: MtoonxtExportProvider | None = None
_EMBEDDED_HOOKS_REGISTERED = False


def register_embedded(
    *,
    mtoonxt_export_provider: MtoonxtExportProvider | None = None,
    register_vrm1_hooks: bool = True,
) -> None:
    """Register the package as a dependency without its standalone UI/RNA.

    Embedded hosts own their Blender UI and persisted properties. The shared
    VRMXT format and export hook remain authoritative, avoiding duplicate RNA
    classes when the standalone add-on is installed separately.
    """

    global _EMBEDDED_PROVIDER, _EMBEDDED_HOOKS_REGISTERED
    if _EMBEDDED_PROVIDER is not None:
        unregister_external_export_provider(_EMBEDDED_PROVIDER)
    _EMBEDDED_PROVIDER = mtoonxt_export_provider
    if _EMBEDDED_PROVIDER is not None:
        register_external_export_provider(_EMBEDDED_PROVIDER)
    if register_vrm1_hooks and not _EMBEDDED_HOOKS_REGISTERED:
        vrm1_hooks.register()
        _EMBEDDED_HOOKS_REGISTERED = vrm1_hooks.hooks_available()


def unregister_embedded() -> None:
    """Reverse only registrations created by :func:`register_embedded`."""

    global _EMBEDDED_PROVIDER, _EMBEDDED_HOOKS_REGISTERED
    if _EMBEDDED_HOOKS_REGISTERED:
        vrm1_hooks.unregister()
        _EMBEDDED_HOOKS_REGISTERED = False
    if _EMBEDDED_PROVIDER is not None:
        unregister_external_export_provider(_EMBEDDED_PROVIDER)
        _EMBEDDED_PROVIDER = None


__all__ = [
    "MtoonxtExportProvider",
    "register_embedded",
    "unregister_embedded",
]
