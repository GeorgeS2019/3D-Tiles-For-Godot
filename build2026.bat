@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
pushd "%ROOT%" >nul

echo [INFO] Starting local Windows 2026 build workflow...

call :ensure_tool git "git --version"
if errorlevel 1 goto :fail

call :ensure_tool cmake "cmake --version"
if errorlevel 1 goto :fail

call :ensure_tool python "python --version"
if errorlevel 1 goto :fail

call :ensure_scons
if errorlevel 1 goto :fail

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
  echo [ERROR] vswhere not found at "%VSWHERE%".
  echo         Install Visual Studio 2026 / Build Tools with C++ workload.
  goto :fail
)

set "VCVARS="
for /f "usebackq delims=" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -find VC\Auxiliary\Build\vcvars64.bat`) do (
  set "VCVARS=%%I"
)
if not defined VCVARS (
  echo [ERROR] Could not locate vcvars64.bat via vswhere.
  goto :fail
)

echo [INFO] Loading MSVC environment: %VCVARS%
call "%VCVARS%"
if errorlevel 1 (
  echo [ERROR] Failed to initialize MSVC environment.
  goto :fail
)

set "GENERATOR="
cmake --help | findstr /c:"Visual Studio 18 2026" >nul
if %errorlevel%==0 (
  set "GENERATOR=Visual Studio 18 2026"
) else (
  call :ensure_tool ninja "ninja --version"
  if errorlevel 1 goto :fail
  set "GENERATOR=Ninja"
)
echo [INFO] Selected CMake generator: %GENERATOR%

if not exist "godot-cpp\.git" (
  echo [INFO] Cloning godot-cpp (godot-4.1.4-stable)...
  git clone --branch godot-4.1.4-stable --depth 1 https://github.com/godotengine/godot-cpp.git godot-cpp
  if errorlevel 1 goto :fail
) else (
  echo [INFO] godot-cpp already present.
)

set "NATIVE_DIR=cesium_godot\native"
set "NATIVE_COMMIT=9f6ae299e2709f866db52c4be29b6c31e10718c8"
if not exist "%NATIVE_DIR%\.git" (
  echo [INFO] Cloning cesium-native...
  git clone https://github.com/CesiumGS/cesium-native.git "%NATIVE_DIR%"
  if errorlevel 1 goto :fail
)

echo [INFO] Syncing cesium-native to CI-pinned commit...
git -C "%NATIVE_DIR%" reset --hard
if errorlevel 1 goto :fail
git -C "%NATIVE_DIR%" clean -fdx
if errorlevel 1 goto :fail
git -C "%NATIVE_DIR%" fetch origin %NATIVE_COMMIT%
if errorlevel 1 goto :fail
git -C "%NATIVE_DIR%" -c advice.detachedHead=false checkout %NATIVE_COMMIT%
if errorlevel 1 goto :fail
git -C "%NATIVE_DIR%" submodule sync --recursive
if errorlevel 1 goto :fail
git -C "%NATIVE_DIR%" submodule update --init --recursive --force
if errorlevel 1 goto :fail

set "CMAKE_FILE=%NATIVE_DIR%\CMakeLists.txt"
python -c "from pathlib import Path; p=Path(r'%CMAKE_FILE%'); t=p.read_text(encoding='utf-8'); o='COMMIT dbe35ceb30c688bf72e952ab23778e009a578f18'; n='COMMIT 2025.09.17';\nif o in t: p.write_text(t.replace(o,n), encoding='utf-8', newline='');\nelif n not in t: raise SystemExit('Expected ezvcpkg commit pin not found in '+str(p))"
if errorlevel 1 (
  echo [ERROR] Failed applying cesium-native vcpkg pin workaround.
  goto :fail
)

set "SDK_ROOT=sdk"
set "SDK_INCLUDE=%SDK_ROOT%\include"
set "SDK_LIB=%SDK_ROOT%\lib"
set "NATIVE_BUILD=%NATIVE_DIR%\build"
if not exist "%NATIVE_BUILD%" mkdir "%NATIVE_BUILD%"
if not exist "%SDK_INCLUDE%" mkdir "%SDK_INCLUDE%"
if not exist "%SDK_LIB%" mkdir "%SDK_LIB%"

echo [INFO] Configuring cesium-native...
if /i "%GENERATOR%"=="Ninja" (
  cmake -S "%NATIVE_DIR%" -B "%NATIVE_BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="%CD%\%SDK_ROOT%"
) else (
  cmake -S "%NATIVE_DIR%" -B "%NATIVE_BUILD%" -G "%GENERATOR%" -A x64 -DCMAKE_INSTALL_PREFIX="%CD%\%SDK_ROOT%"
)
if errorlevel 1 goto :fail

echo [INFO] Building and installing cesium-native SDK...
cmake --build "%NATIVE_BUILD%" --config Release --target install
if errorlevel 1 goto :fail

echo [INFO] Running SCons extension build using local staged SDK when present...
scons platform=windows arch=x64 compileTarget=extension target=template_release buildCesium=true
if errorlevel 1 goto :fail

echo [OK] Build finished successfully.
echo [OK] cesium-native build dir: "%NATIVE_BUILD%"
echo [OK] staged SDK include: "%CD%\%SDK_INCLUDE%"
echo [OK] staged SDK lib: "%CD%\%SDK_LIB%"
goto :eof

:ensure_tool
where %~1 >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] Required tool '%~1' not found in PATH.
  exit /b 1
)
%~2 >nul 2>&1
if %errorlevel% neq 0 (
  echo [ERROR] Tool '%~1' is present but not runnable.
  exit /b 1
)
exit /b 0

:ensure_scons
where scons >nul 2>&1
if %errorlevel%==0 exit /b 0
echo [INFO] SCons not found. Installing with pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 exit /b 1
python -m pip install scons
if %errorlevel% neq 0 exit /b 1
where scons >nul 2>&1
if %errorlevel% neq 0 exit /b 1
exit /b 0

:fail
echo [FAIL] Local Windows 2026 build workflow failed.
popd >nul
exit /b 1
