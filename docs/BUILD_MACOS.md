# Building on macOS (Intel and Apple Silicon)

Build a separate extension for `x86_64` (Intel) or `arm64` (Apple Silicon).
The architecture is passed to godot-cpp, Cesium Native, vcpkg and litehtml.
If omitted, `arch` defaults to the current host architecture. Universal
builds are not supported; build each architecture separately.

The original Apple Silicon guide was tested on M3 Pro with Godot 4.6.2.
Intel release and debug builds were tested on an Intel Core i9 Mac with
macOS 15.8.1, Xcode 26.3 and Godot 4.6.2 (headless import and class
registration). The ARM litehtml archives were also cross-built on Intel;
a full ARM extension build was not repeated.

## Prerequisites

```bash
brew install pkg-config cmake ninja openssl@3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install scons
```

- `pkg-config`: required by vcpkg (fmt fails to build without it).
- `openssl@3`: macOS's bundled LibreSSL breaks Cesium Native's SSL build.
- `cmake` + `ninja`: C++ build tools.
- `scons`: the build orchestrator used by this repo.

## Environment

Export OpenSSL root so Cesium Native picks up Homebrew's OpenSSL
instead of the system LibreSSL:

```bash
export OPENSSL_ROOT_DIR=$(brew --prefix openssl@3)
export OPENSSL_DIR=$(brew --prefix openssl@3)
```

## Build

Run from the repository root. The first run clones the pinned godot-cpp,
Cesium Native and litehtml sources. `buildCesium=yes` builds Cesium Native
without an interactive prompt.

Intel:

```bash
scons -f SConstruct.py platform=macos arch=x86_64 compileTarget=extension buildCesium=yes \
      target=template_release production=yes
```

Apple Silicon:

```bash
scons -f SConstruct.py platform=macos arch=arm64 compileTarget=extension buildCesium=yes \
            target=template_release production=yes
```

Build takes ~15–20 minutes on M3 Pro. Output (replace `arm64` with
`x86_64` for Intel):

```
godot3dtiles/addons/cesium_godot/lib/libGodot3DTiles.macos.template_release.arm64.dylib
```

(Mach-O 64-bit shared library for the selected architecture.)

Cesium Native uses `cesium_godot/native/build-macos-<arch>/` and vcpkg's
`x64-osx` or `arm64-osx` triplet. litehtml is built from commit
`35ecd69d05e72b0148204a576db62c2148084193` (matching the bundled headers)
into `cesium_godot/third_party/litehtml/macos/<arch>/`. These generated
archives are not committed. The older shared macOS archives are not used.

For later extension-only rebuilds, use `buildCesium=no`. Build the editor
variant with the same command and `target=template_debug`; it can reuse
the already-built dependencies. To limit parallel CMake build jobs, set
`CMAKE_BUILD_PARALLEL_LEVEL` (and use SCons `-j` for the extension).

After updating an existing macOS checkout, run `buildCesium=yes` once to
populate the new architecture-specific build directory before using
`buildCesium=no`.

Build-script regression tests:

```bash
python -m unittest discover -s tests -v
```

## Wiring into a Godot project

1. Copy `godot3dtiles/addons/cesium_godot` into your project's `addons/`.
2. `Godot3DTiles.gdextension` references both architectures and both
   `template_debug` and `template_release`. Build `template_debug` for
   the editor and `template_release` for exported release projects.
3. Enable the plugin in `Project → Project Settings → Plugins`
   (or append `"res://addons/cesium_godot/plugin.cfg"` to
   `editor_plugins/enabled` in `project.godot`).

Verify the GDExtension loaded:

```bash
godot --headless --path /path/to/project --script /path/to/probe.gd
```

where `probe.gd` does:

```gdscript
extends SceneTree
func _init():
    var success := true
    for class_name_to_check in ["CesiumGeoreference", "Cesium3DTileset", "CesiumIonRasterOverlay"]:
        var registered := ClassDB.class_exists(class_name_to_check)
        print(class_name_to_check, " registered: ", registered)
        success = success and registered
    quit(0 if success else 1)
```

Expected: all three print `true`.

## Known quirks on macOS

- On a fresh project, immediately quitting a headless editor after import
  (`--import --quit`) can crash during deferred extension documentation
  generation (observed with Godot 4.6.2 and 4.7.2 Mono). Headless editor
  startup with `--editor --quit-after 1000` completed cleanly, as did the
  runtime registration probe. This is separate from building/loading the
  Intel dylibs.
- `CesiumDynamicCamera`'s default `move_speed = 100` m/s is designed for
  globe-scale navigation and is unusable at building scale. For
  Cartographic origin at city level, either lower `move_speed` or write
  a custom camera that calls `tileset.update_tileset(camera_xform)` each
  frame.
- The default shaders reference
  `res://Shaders/spatial_texture_rotation.gdshader` which does not ship in
  `addons/cesium_godot/`. Missing-shader errors appear on scene load but
  do not block tile streaming. (Tracking separately.)
- `Godot3DTiles.gdextension` lists debug and release libraries for both
  Intel and Apple Silicon. Distributing pre-built binaries of both
  variants would unblock users who can't compile C++.

## Rationale

Several users on forums ask whether the plugin "works on Mac". The
answer is "yes" for both Intel and Apple Silicon when built for the
correct architecture. This guide covers the required toolchain and
dependency configuration.
