"""Ensure the macOS build-directory changes preserve other platforms."""
import subprocess
import unittest
from unittest.mock import patch

import CesiumBuildUtils as build


class NonMacOSBuildTests(unittest.TestCase):
    def test_native_configuration_preserves_in_source_builds(self):
        for platform_name, operating_system, triplet in (
            ("win32", "nt", "x64-windows-static"),
            ("linux", "posix", "x64-linux"),
        ):
            with self.subTest(platform=platform_name):
                source_directory = "/native-source"
                command = [
                    "cmake", "-DCMAKE_BUILD_TYPE=Release",
                    "-DCESIUM_MSVC_STATIC_RUNTIME_ENABLED=ON",
                    "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", "-DGIT_LFS_SKIP_SMUDGE=1",
                    f"-DVCPKG_TRIPLET={triplet}",
                    "-S", source_directory, "-B", source_directory,
                ]
                with patch.object(build.sys, "platform", platform_name), \
                     patch.object(build.os, "name", operating_system), \
                     patch.dict(build.os.environ), \
                     patch.object(build, "scons_to_abs_path", autospec=True, return_value=source_directory), \
                     patch.object(build.subprocess, "run", autospec=True, return_value=subprocess.CompletedProcess(command, 0)) as run:
                    build.configure_native({"compileTarget": "extension"})
                    self.assertEqual(build.get_native_build_dir(), source_directory)
                    self.assertEqual(build.os.environ["VCPKG_TRIPLET"], triplet)
                    run.assert_called_once_with(command)

    def test_linux_build_uses_native_source_directory(self):
        command = ["cmake", "--build", "/native-source"]
        result = subprocess.CompletedProcess(command, 0)
        with patch.object(build.sys, "platform", "linux"), \
             patch.object(build, "get_root_dir_native", autospec=True, return_value="/native-source"), \
             patch.object(build.subprocess, "run", autospec=True, return_value=result) as run:
            self.assertEqual(build.build_native_linux(), result)
            run.assert_called_once_with(command)

    def test_windows_build_runs_msbuild_in_native_source_directory(self):
        command = ["MSBuild.exe", "cesium-native.sln", "/property:Configuration=Release"]
        result = subprocess.CompletedProcess(command, 0)
        with patch.object(build.sys, "platform", "win32"), \
             patch.object(build, "get_root_dir_native", autospec=True, return_value="/native-source"), \
             patch.object(build, "find_ms_build", autospec=True, return_value="MSBuild.exe"), \
             patch.object(build.subprocess, "run", autospec=True, return_value=result) as run:
            self.assertEqual(build.build_native_win(), result)
            run.assert_called_once_with(command, cwd="/native-source")


if __name__ == "__main__":
    unittest.main()
