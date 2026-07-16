#!/usr/bin/env bash
# ponytail: one-shot Windows installer for mtkclient
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MTK_DIR="$REPO_ROOT/mtkclient"

WGET_OPTS="-q --show-progress"

check_cmd() { command -v "$1" &>/dev/null; }

step() { echo; echo "==> $1"; }

# Determine install method: use choco, winget, or direct download
install_winget() {
    local pkg="$1"
    winget install --silent --accept-package-agreements "$pkg"
}

install_choco() {
    local pkg="$1"
    choco install -y "$pkg"
}

ensure_package() {
    local name="$1" winget_id="$2" choco_id="$3"
    if check_cmd "$name"; then
        echo "  [ok] $name already installed"
        return 0
    fi
    if check_cmd winget && [ -n "$winget_id" ]; then
        install_winget "$winget_id"
        return
    fi
    if check_cmd choco && [ -n "$choco_id" ]; then
        install_choco "$choco_id"
        return
    fi
    echo "  [!!] Cannot install $name - install manually or via winget/choco"
    return 1
}

install_python() {
    if check_cmd python; then
        local ver
        ver=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0")
        echo "  [ok] Python $ver found"
        if python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
            return 0
        fi
        echo "  Python too old ($ver), upgrading..."
    fi
    if check_cmd winget; then
        winget install --silent --accept-package-agreements "Python.Python.3.13"
    elif check_cmd choco; then
        choco install -y python --version=3.13.0
    else
        # Fallback: download and run the official installer
        local tmpdir pyver
        tmpdir=$(mktemp -d)
        pyver="3.13.14"
        echo "  Downloading Python $pyver..."
        curl -L -o "$tmpdir/python-installer.exe" \
            "https://www.python.org/ftp/python/$pyver/python-${pyver}-amd64.exe"
        "$tmpdir/python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        rm -rf "$tmpdir"
    fi
    # Refresh PATH
    export PATH="$PATH:/c/Program Files/Python313:/c/Program Files/Python313/Scripts"
    # Wait for installer to finish, rehash
    sleep 2
    hash -r 2>/dev/null || true
    check_cmd python || { echo "  [!!] Python install failed"; exit 1; }
}

install_vs_build_tools() {
    if check_cmd "cl.exe" && check_cmd "link.exe"; then
        echo "  [ok] VS Build Tools present"
        return 0
    fi
    echo "  Downloading VS Build Tools..."
    local tmpdir
    tmpdir=$(mktemp -d)
    curl -L -o "$tmpdir/vs_buildtools.exe" \
        "https://aka.ms/vs/17/release/vs_buildtools.exe"
    # Minimal C++ build tools install (no full VS)
    "$tmpdir/vs_buildtools.exe" --quiet --wait --norestart \
        --installPath "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools" \
        --add "Microsoft.VisualStudio.Workload.VCTools" \
        --includeRecommended \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.10240" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.14393" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.15063" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.16299" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.17134" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.17763" \
        --remove "Microsoft.VisualStudio.Component.Windows10SDK.18362" \
        --remove "Microsoft.VisualStudio.Component.Windows11SDK.22000" \
        --remove "Microsoft.VisualStudio.Component.Windows11SDK.22621" 2>/dev/null || true
    rm -rf "$tmpdir"
    echo "  VS Build Tools installer done (may need reboot for cl.exe to appear)"
}

install_winfsp() {
    if [ -d "/c/Program Files (x86)/WinFsp" ] || [ -d "/c/Program Files/WinFsp" ]; then
        echo "  [ok] WinFsp installed"
        return 0
    fi
    local tmpdir
    tmpdir=$(mktemp -d)
    echo "  Downloading WinFsp..."
    curl -L -o "$tmpdir/winfsp.msi" \
        "https://github.com/winfsp/winfsp/releases/download/v2.1/winfsp-2.1.25156.msi"
    msiexec /i "$tmpdir/winfsp.msi" /quiet /norestart
    rm -rf "$tmpdir"
    echo "  WinFsp installed"
}

install_usbdk() {
    if [ -d "/c/Program Files/UsbDk" ]; then
        echo "  [ok] UsbDk installed"
        return 0
    fi
    local tmpdir
    tmpdir=$(mktemp -d)
    echo "  Downloading UsbDk..."
    # ponytail: pinned 1.00-22, update URL if upstream changes
    curl -L -o "$tmpdir/usbdk.msi" \
        "https://github.com/daynix/UsbDk/releases/download/v1.00-22/UsbDk_1.0.22_x64.msi"
    msiexec /i "$tmpdir/usbdk.msi" /quiet /norestart
    rm -rf "$tmpdir"
    echo "  UsbDk installed"
    echo "  Reboot recommended for UsbDk driver to become active"
}

check_admin() {
    if check_cmd net; then
        net session &>/dev/null && return 0 || return 1
    fi
    return 1
}

echo "===================================================="
echo "  MTKClient Windows Installer"
echo "===================================================="

# Refresh PATH so winget/choco are found if just installed
export PATH="$PATH:/c/Program Files/Python313:/c/Program Files/Python313/Scripts"
hash -r 2>/dev/null || true

# Some steps need admin (winget, msiexec installs, udev-like driver setup)
if ! check_admin; then
    echo "  WARNING: Run this script as Administrator for best results"
    echo "  (Right-click Git Bash -> Run as Administrator)"
    echo
fi

step "1/8: Installing Python 3.8+..."
install_python

step "2/8: Installing Git..."
ensure_package git "Git.Git" "git.install" || true  # non-fatal, clone works with curl too

step "3/8: Installing Visual Studio Build Tools..."
install_vs_build_tools

step "4/8: Installing WinFsp (FUSE support)..."
install_winfsp

step "5/8: Installing UsbDk (USB driver)..."
install_usbdk

step "6/8: Getting mtkclient source..."
TARGET_DIR="/c/mtkclient"
if [ -d "$MTK_DIR" ]; then
    echo "  Found local mtkclient at $MTK_DIR"
    echo "  Copying to $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
    cp -r "$MTK_DIR" "$TARGET_DIR"
else
    if [ -d "$TARGET_DIR" ]; then
        echo "  [ok] Already cloned at $TARGET_DIR, updating..."
        cd "$TARGET_DIR" && git pull --ff-only 2>/dev/null || true
    else
        echo "  Cloning from GitHub..."
        git clone --recursive https://github.com/bkerler/mtkclient "$TARGET_DIR" 2>/dev/null || {
            echo "  Git unavailable, downloading ZIP..."
            curl -L -o /tmp/mtkclient.zip \
                "https://github.com/bkerler/mtkclient/archive/refs/heads/main.zip"
            unzip -q /tmp/mtkclient.zip -d /c/
            mv /c/mtkclient-main "$TARGET_DIR"
            rm -f /tmp/mtkclient.zip
        }
    fi
fi

# Copy bundled libusb DLLs to SysWOW64/System32 for pyusb to find
if [ -f "$TARGET_DIR/mtkclient/Windows/libusb-1.0.dll" ]; then
    step "  Copying libusb DLLs to system..."
    cp "$TARGET_DIR/mtkclient/Windows/libusb-1.0.dll" \
        "/c/Windows/System32/libusb-1.0.dll" 2>/dev/null || true
    cp "$TARGET_DIR/mtkclient/Windows/libusb32-1.0.dll" \
        "/c/Windows/SysWOW64/libusb-1.0.dll" 2>/dev/null || true
fi

step "7/8: Installing Python dependencies..."
cd "$TARGET_DIR"
python -m pip install --upgrade pip wheel setuptools
# Install pycryptodome with build isolation off to use VS tools
pip install --no-build-isolation pycryptodome pycryptodomex 2>/dev/null || \
    pip install pycryptodome pycryptodomex
# Install main deps
pip install -r requirements.txt --no-build-isolation 2>/dev/null || \
    pip install -r requirements.txt
# Install mtkclient itself
pip install -e .

step "8/8: Creating launcher shortcuts..."
# Create a batch launcher that works from anywhere
cat > "/c/mtkclient/mtk.bat" << 'BATEOF'
@echo off
title MTKClient
python "%~dp0mtk.py" %*
BATEOF

cat > "/c/mtkclient/mtk_gui.bat" << 'BATEOF'
@echo off
title MTKClient - GUI
python "%~dp0mtk_gui.py"
BATEOF

# Add to PATH via registry for current user
if check_cmd reg; then
    reg add "HKCU\Environment" /f /v "MTKCLIENT_PATH" /t REG_SZ /d "C:\mtkclient" 2>/dev/null || true
    # Append to PATH if not already there
    current_path=$(reg query "HKCU\Environment" /v PATH 2>/dev/null | grep -i "C:\\mtkclient" || echo "")
    if [ -z "$current_path" ]; then
        setx PATH "%PATH%;C:\mtkclient" 2>/dev/null || true
    fi
fi

echo
echo "===================================================="
echo "  MTKClient Windows Installation Complete!"
echo "===================================================="
echo "   Location: C:\\mtkclient"
echo "   Run:      mtk (CLI)"
echo "   Run:      mtk_gui (GUI)"
echo
echo "   Post-install steps:"
echo "   1. REBOOT (for UsbDk driver and VS tools)"
echo "   2. Connect your MTK device in BROM mode"
echo "   3. Verify with:  mtk printgpt"
echo "===================================================="
