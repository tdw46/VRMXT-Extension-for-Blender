# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`) on top of stock
[VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender)
**4.6.0** or later (VRM 1.0 `Vrm1ImportUserExtension` /
`Vrm1ExportUserExtension` hooks).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

Material PROPERTIES: parent panel **VRMXT Material** holds materials override and
MToonXT stencil.

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_sprite_particle` | JSON → property groups + GeoNodes preview | property groups → JSON | armature UIList | Flat emitters; offsets via helper Empty; preview via shared `VRMXT_Particle` node group (excluded from export). |
| `VRMXT_materials_override` | JSON → material store | material store → JSON | VRMXT Material | Unity slots, catalog shaders, textures. Schema: `idType`/`id` (+ optional `properties[]`). |
| `VRMXT_materials_mtoonxt` | JSON → material ops and root relationships | material/Scene settings → JSON | VRMXT Material + Scene | Body/outline shorthand plus portable cross-material presentation, depth tests, and depth publication. No EEVEE clip. Runtime stencil is supplied by a consumer such as UniVRMXT. |

## Requirements

- Blender **4.2** inclusive through **&lt;5.3**
- [VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender/releases/tag/v4.6.0) **4.6.0+** (VRM 1.0 third-party hooks)

## Install

1. Install and enable VRM format 4.6.0 or later.
2. Build the standalone extension from the shared source package:

   ```bash
   blender --command extension build --source-dir src/io_scene_vrmxt
   ```

3. Install the generated `vrmxt-0.3.0.zip` through Blender's Extensions UI.
   Its extension ID is `vrmxt`.
4. Enable **VRMXT Extensions**. Stock VRM discovers `Vrm1ImportUserExtension` /
   `Vrm1ExportUserExtension` on this add-on's root module.

## Embedded dependency mode

The same source tree can be vendored under another Blender extension. In that
mode, import the vendored package by its nested package name and call
`integration.register_embedded(...)`. VRMXT still owns and registers its
portable Scene/Material properties; embedded registration omits only standalone
panels and operators. A host can mirror its UI model with
`integration.sync_bvt_scene_to_vrmxt(scene)` and call
`integration.export_vrm_with_vrmxt(...)`. Existing shared RNA from an enabled
standalone copy is reused rather than duplicated.

The Blender manifest lives beside the Python package so the source directory is
directly buildable as a standalone extension. Embedded hosts ignore that data
file and load the same package through `integration`, so standalone and embedded
installations cannot drift into separate implementations.

Standalone installs expose **File > Export > VRM with VRMXT Extensions**. The
operator calls the installed VRM add-on first, uses Extended VRM hooks when
available, and atomically adds missing VRMXT JSON to the completed GLB as a
fallback. Original VRM materials and all stock VRM 0.x/1.x features remain
authoritative. The mapping, hook transaction, serializer, and fallback all live
inside VRMXT; embedded hosts only synchronize properties and call this API.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src tests
ruff format --check src tests
```

## License

MIT. See [LICENSE](LICENSE).
