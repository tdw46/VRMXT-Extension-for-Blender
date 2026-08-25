# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`) on top of
[Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

Material PROPERTIES: parent panel **VRMXT Material** holds materials override and
MToonXT stencil.

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_sprite_particle` | JSON → property groups + GeoNodes preview | property groups → JSON | armature UIList | Flat emitters; offsets via helper Empty; preview via shared `VRMXT_Particle` node group (excluded from export). |
| `VRMXT_materials_override` | JSON → material store | material store → JSON | VRMXT Material | Unity slots, catalog shaders, textures. Schema: `idType`/`id` (+ optional `properties[]`). |
| `VRMXT_materials_mtoonxt` | JSON → material stencil ops | material settings → JSON | VRMXT Material | Body/outline `write` / `inside` / `insideOverlay` / `outside` / outline `same`. No EEVEE clip. Warns when a writer is Transparent (or Cutout vs Opaque) and a clip reader would draw earlier. Runtime stencil is Unity. |

## Requirements

- Blender **4.2** inclusive through **&lt;5.3**
- [Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender) with `io_scene_vrm.extension_hooks` (VRM 1.0 hooks)

## Install

1. Install and enable Extended VRM for Blender.
2. Build the standalone extension from the shared source package:

   ```bash
   blender --command extension build --source-dir src/io_scene_vrmxt
   ```

3. Install the generated `vrmxt-0.3.0.zip` through Blender's Extensions UI.
   Its extension ID is `vrmxt`.
4. Enable **VRMXT Extensions**.

## Embedded dependency mode

The same source tree can be vendored under another Blender extension. In that
mode, import the vendored package by its nested package name and call
`integration.register_embedded(...)`. Embedded registration deliberately omits
VRMXT's standalone panels, operators, and RNA property groups so the host can
own its UI and persisted authoring data without class collisions. The shared
format parser, serializer, VRM 1 hook adapter, and portable GLB patcher remain
available in both modes.

The Blender manifest lives beside the Python package so the source directory is
directly buildable as a standalone extension. Embedded hosts ignore that data
file and load the same package through `integration`, so standalone and embedded
installations cannot drift into separate implementations.

`portable_exporter.patch_exported_vrm()` wraps an installed VRM exporter rather
than replacing it: the host exports its normal VRM first, then atomically adds
VRMXT JSON to the completed GLB. Original VRM materials and all stock
extensions remain authoritative.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src tests
ruff format --check src tests
```

## License

MIT. See [LICENSE](LICENSE).
