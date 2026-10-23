"""Build-script regression tests. Run with: python -m unittest discover -s tests -v."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import CesiumBuildUtils as build


class MacOSBuildTests(unittest.TestCase):
    def setUp(self):
        self.platform = patch.object(build.sys, "platform", "darwin")
        self.platform.start()
        self.addCleanup(self.platform.stop)
        self.architecture = patch.object(build, "macosArchitecture", None)
        self.architecture.start()
        self.addCleanup(self.architecture.stop)
        build.get_compile_target_definition({"compileTarget": "extension"})

    def test_architecture_triplets_and_build_paths(self):
        for architecture, triplet in (("x86_64", "x64-osx"), ("arm64", "arm64-osx")):
            with self.subTest(architecture=architecture):
                arguments = {"arch": architecture}
                build.configure_macos_architecture(arguments)
                self.assertEqual(arguments, {"arch": architecture})
                self.assertEqual(build.determine_triplet(), triplet)
                self.assertEqual(
                    build.get_native_build_dir(),
                    os.path.join(build.get_root_dir_native(), f"build-macos-{architecture}"),
                )

    def test_unspecified_architecture_uses_host(self):
        for architecture in ("x86_64", "arm64"):
            with self.subTest(architecture=architecture), patch.object(build.platform, "machine", return_value=architecture):
                build.macosArchitecture = None
                arguments = {}
                build.configure_macos_architecture(arguments)
                self.assertEqual(arguments, {"arch": architecture})

    def test_unsupported_architectures_fail(self):
        for architecture in ("universal", "x86_32", "unknown"):
            with self.subTest(architecture=architecture), self.assertRaisesRegex(ValueError, "Unsupported macOS architecture"):
                build.configure_macos_architecture({"arch": architecture})

    def test_cmake_configuration_selects_matching_architecture(self):
        for architecture, triplet in (("x86_64", "x64-osx"), ("arm64", "arm64-osx")):
            with self.subTest(architecture=architecture):
                build.configure_macos_architecture({"arch": architecture})
                command = [
                    "cmake", "-DCMAKE_BUILD_TYPE=Release", "-DCESIUM_MSVC_STATIC_RUNTIME_ENABLED=ON",
                    "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", "-DGIT_LFS_SKIP_SMUDGE=1",
                    f"-DVCPKG_TRIPLET={triplet}", "-S", build.get_root_dir_native(),
                    "-B", build.get_native_build_dir(), f"-DCMAKE_OSX_ARCHITECTURES={architecture}",
                ]
                with patch.object(build.subprocess, "run", autospec=True, return_value=subprocess.CompletedProcess(command, 0)) as run:
                    build.configure_native({"compileTarget": "extension"})
                    run.assert_called_once_with(command)

    def test_litehtml_requires_both_architecture_specific_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "litehtml-src")
            source.mkdir()
            for architecture in ("x86_64", "arm64"):
                with self.subTest(architecture=architecture):
                    output = Path(directory, "litehtml", "macos", architecture)
                    output.mkdir(parents=True)
                    (output / "liblitehtml.a").touch()
                    # One archive alone must not count as a complete build.
                    error = subprocess.CalledProcessError(1, ["cmake"])
                    with patch.object(build, "scons_to_abs_path", return_value=directory), patch.object(build.subprocess, "run", autospec=True, side_effect=error) as run:
                        with self.assertRaises(subprocess.CalledProcessError):
                            build.build_litehtml(architecture)
                        self.assertEqual(run.call_args.args[0][2], f"-DCMAKE_OSX_ARCHITECTURES={architecture}")
                        self.assertEqual(run.call_args.kwargs, {"cwd": str(source / f"build-macos-{architecture}"), "check": True})
                    (output / "libgumbo.a").touch()
                    with patch.object(build, "scons_to_abs_path", return_value=directory), patch.object(build.subprocess, "run", autospec=True) as run:
                        build.build_litehtml(architecture)
                        run.assert_not_called()

    def test_litehtml_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(build, "scons_to_abs_path", return_value=directory):
            with self.assertRaisesRegex(FileNotFoundError, "litehtml source not found"):
                build.build_litehtml("x86_64")

    def test_litehtml_missing_build_output_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(build, "scons_to_abs_path", return_value=directory):
            Path(directory, "litehtml-src").mkdir()
            with patch.object(build.subprocess, "run", autospec=True, return_value=subprocess.CompletedProcess(["cmake"], 0)):
                with self.assertRaisesRegex(FileNotFoundError, "did not produce liblitehtml.a"):
                    build.build_litehtml("x86_64")

    def test_native_build_failure_is_not_reported_as_success(self):
        command = ["cmake", "--build", build.get_native_build_dir()]
        with patch.object(build, "configure_native", autospec=True), patch.object(build, "build_native_macos", autospec=True, return_value=subprocess.CompletedProcess(command, 1)), patch.object(build, "clean_cesium_definitions", autospec=True) as clean:
            with self.assertRaises(subprocess.CalledProcessError):
                build.compile_native({"buildCesium": "yes"})
            clean.assert_not_called()

    def test_extension_manifest_preserves_both_architectures(self):
        manifest = Path(__file__).resolve().parents[1] / "godot3dtiles/addons/cesium_godot/Godot3DTiles.gdextension"
        entries = dict(line.split(" = ", 1) for line in manifest.read_text().splitlines() if " = " in line)
        for architecture in ("x86_64", "arm64"):
            for mode, target in (("debug", "template_debug"), ("release", "template_release")):
                with self.subTest(architecture=architecture, mode=mode):
                    self.assertEqual(entries[f"macos.{mode}.{architecture}"], f'"res://addons/cesium_godot/lib/libGodot3DTiles.macos.{target}.{architecture}.dylib"')


if __name__ == "__main__":
    unittest.main()
