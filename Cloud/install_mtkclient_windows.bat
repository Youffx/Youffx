@echo off
title MTKClient Windows Installer
setlocal enabledelayedexpansion

set "TARGET_DIR=C:\mtkclient"
set "PY_VER=3.13.14"

:check_admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Run as Administrator ^(right-click ^> Run as administrator^)
    echo.
)

echo ====================================================
echo   MTKClient Windows Installer
echo ====================================================

:step_python
echo.
echo ^=^=^> 1/7: Installing Python %PY_VER%...
where python >nul 2>&1
if %errorlevel% equ 0 (
    python --version
    python -c "import sys; exit(0 if sys.version_info>=(3,8) else 1)" 2>nul && goto step_git
)
where winget >nul 2>&1
if %errorlevel% equ 0 (
    winget install --silent --accept-package-agreements "Python.Python.3.13" && goto step_git
)
echo Downloading Python %PY_VER%...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe' -OutFile '%TEMP%\python-installer.exe'}"
start /wait "" "%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del "%TEMP%\python-installer.exe" 2>nul

:step_git
echo.
echo ^=^=^> 2/7: Installing Git...
where git >nul 2>&1
if %errorlevel% equ 0 ( echo   [ok] Git found && goto step_vs )
where winget >nul 2>&1
if %errorlevel% equ 0 (
    winget install --silent --accept-package-agreements "Git.Git" && goto step_vs
)
echo   [!!] Git not installed, will use ZIP download fallback.

:step_vs
echo.
echo ^=^=^> 3/7: Installing Visual Studio Build Tools...
where cl >nul 2>&1
if %errorlevel% equ 0 ( echo   [ok] VS Build Tools found && goto step_winfsp )
echo Downloading VS Build Tools...
powershell -Command "& {Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe' -OutFile '%TEMP%\vs_buildtools.exe'}"
start /wait "" "%TEMP%\vs_buildtools.exe" --quiet --wait --norestart ^
    --installPath "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools" ^
    --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended
del "%TEMP%\vs_buildtools.exe" 2>nul

:step_winfsp
echo.
echo ^=^=^> 4/7: Installing WinFsp ^(FUSE support^)...
if exist "%ProgramFiles(x86)%\WinFsp" ( echo   [ok] WinFsp found && goto step_usbdk )
if exist "%ProgramFiles%\WinFsp" ( echo   [ok] WinFsp found && goto step_usbdk )
echo Downloading WinFsp...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/winfsp/winfsp/releases/download/v2.1/winfsp-2.1.25156.msi' -OutFile '%TEMP%\winfsp.msi'}"
start /wait msiexec /i "%TEMP%\winfsp.msi" /quiet /norestart
del "%TEMP%\winfsp.msi" 2>nul

:step_usbdk
echo.
echo ^=^=^> 5/7: Installing UsbDk ^(USB driver^)...
if exist "%ProgramFiles%\UsbDk" ( echo   [ok] UsbDk found && goto step_clone )
echo Downloading UsbDk...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/daynix/UsbDk/releases/download/v1.00-22/UsbDk_1.0.22_x64.msi' -OutFile '%TEMP%\usbdk.msi'}"
start /wait msiexec /i "%TEMP%\usbdk.msi" /quiet /norestart
del "%TEMP%\usbdk.msi" 2>nul

:step_clone
echo.
echo ^=^=^> 6/7: Getting mtkclient source...
if exist "%TARGET_DIR%" (
    echo   [ok] Already exists at %TARGET_DIR%, updating...
    cd /d "%TARGET_DIR%" && git pull --ff-only 2>nul || echo   [i] Will re-clone if needed
    goto step_libusb
)
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo Cloning from GitHub...
    git clone --recursive https://github.com/bkerler/mtkclient "%TARGET_DIR%" 2>nul
    if exist "%TARGET_DIR%" goto step_libusb
)
echo Downloading ZIP...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/bkerler/mtkclient/archive/refs/heads/main.zip' -OutFile '%TEMP%\mtkclient.zip'}"
powershell -Command "& {Expand-Archive -Path '%TEMP%\mtkclient.zip' -DestinationPath '%TEMP%' -Force}"
if exist "%TEMP%\mtkclient-main" (
    rd /s /q "%TARGET_DIR%" 2>nul
    move "%TEMP%\mtkclient-main" "%TARGET_DIR%" >nul
)
del "%TEMP%\mtkclient.zip" 2>nul

:step_libusb
echo.
echo Copying libusb DLLs to system...
if exist "%TARGET_DIR%\mtkclient\Windows\libusb-1.0.dll" (
    copy /y "%TARGET_DIR%\mtkclient\Windows\libusb-1.0.dll" "%SystemRoot%\System32\libusb-1.0.dll" >nul 2>&1
)
if exist "%TARGET_DIR%\mtkclient\Windows\libusb32-1.0.dll" (
    copy /y "%TARGET_DIR%\mtkclient\Windows\libusb32-1.0.dll" "%SystemRoot%\SysWOW64\libusb-1.0.dll" >nul 2>&1
)

:step_pip
echo.
echo ^=^=^> 7/7: Installing Python dependencies...
cd /d "%TARGET_DIR%"
python -m pip install --upgrade pip wheel setuptools
pip install pycryptodome pycryptodomex 2>nul
pip install -r requirements.txt
pip install -e .

:step_launcher
echo.
cd /d "%TARGET_DIR%"
copy /y NUL mtk.bat >nul 2>&1
(
echo @echo off
echo title MTKClient
echo python "%%~dp0mtk.py" %%*
) > mtk.bat
(
echo @echo off
echo title MTKClient - GUI
echo python "%%~dp0mtk_gui.py"
) > mtk_gui.bat

echo Adding to PATH...
setx PATH "%%PATH%%;%TARGET_DIR%" >nul 2>&1

echo.
echo ====================================================
echo   MTKClient Windows Installation Complete!
echo ====================================================
echo   Location: %TARGET_DIR%
echo   Run:      mtk (CLI)
echo   Run:      mtk_gui (GUI)
echo.
echo   Post-install steps:
echo   1. REBOOT ^(for UsbDk driver and VS tools^)
echo   2. Connect your MTK device in BROM mode
echo   3. Verify with:  mtk printgpt
echo ====================================================
echo.
pause
