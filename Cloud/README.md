# ROM Porting Guide: Redmi Note 10S (rosemary)

**Stock ROM:** MIUI 14.0.5.0 (TKLIDXM) — Android 13  
**Port ROM:** HyperOS 3.0 (OS3.0.303.0.WNTMIXM) — Android 16

---

## 1. Device Overview

| Spec | Detail |
|------|--------|
| Device | Xiaomi Redmi Note 10S |
| Codename | rosemary (also maltose, secret) |
| SoC | MediaTek Helio G95 (MT6785V/CD) |
| CPU | 2× Cortex-A76 @ 2.05GHz + 6× Cortex-A55 @ 2.0GHz |
| GPU | Mali-G76 MC4 @ 900MHz |
| RAM | 6/8GB LPDDR4X |
| Display | 6.43" AMOLED 1080×2400 |
| Battery | 5000mAh, 33W |
| Partitions | A/B (seamless updates) |
| Kernel | Linux 4.14.x (MediaTek) |

---

## 2. ROM Analysis

### Stock ROM: `miui_ROSEMARYIDGlobal_V14.0.5.0.TKLIDXM`

| Property | Value |
|----------|-------|
| Android | 13 (SDK 33) |
| MIUI | 14.0.5.0 |
| Security patch | 2024-04-01 |
| Format | OTA payload (payload.bin v2) |
| Build fingerprint | `Redmi/rosemary/rosemary:13/TP1A.220624.014/V14.0.5.0.TKLIDXM:user/release-keys` |

**Partitions inside payload.bin:**

| Partition | Size | Description |
|-----------|------|-------------|
| system | 1357 MB | Android framework |
| vendor | 1536 MB | Device blobs, HALs, firmware |
| product | 4298 MB | Product customizations |
| system_ext | 755 MB | Extended system |
| boot | 64 MB | Kernel + ramdisk |
| vbmeta | 4 KB | Verified boot metadata |
| vbmeta_system | 4 KB | System vbmeta |
| vbmeta_vendor | 4 KB | Vendor vbmeta |
| dtbo | 56 KB | Device tree blob overlay |
| preloader_raw | 340 KB | MediaTek preloader |
| lk | 1.7 MB | Little Kernel (U-Boot) |
| tee | 2.4 MB | TrustZone OS |
| md1img | 57.4 MB | Modem firmware |
| scp | 2.2 MB | System Control Processor |
| spmfw | 16 KB | Power management firmware |
| sspm | 648 KB | System Security Processor |
| gz | 1.2 MB | Gunyah hypervisor |
| audio_dsp | 1.3 MB | Audio DSP firmware |
| cam_vpu1 | 1.1 MB | Camera VPU1 |
| cam_vpu2 | 11.6 MB | Camera VPU2 |
| cam_vpu3 | 140 KB | Camera VPU3 |
| mi_ext | 276 KB | MIUI extensions |

### Port ROM: `rosemary_global-hybrid_full-OS3.0.303.0.WNTMIXM-user-16.0`

| Property | Value |
|----------|-------|
| Android | 16 (from filename OS3.0 = HyperOS 3.0) |
| Version | HyperOS 3.0.303.0 |
| Format | Custom zip (FBFlasher + payload.bin + recovery update-binary) |
| Zip contents | `FBFlasher-L.sh`, `FBFlasher.bat`, `META-INF/`, `payload.bin` |

**Key differences from stock:**
- Can be flashed via **fastboot** (FBFlasher scripts) or **custom recovery** (update-binary)
- Zip-level metadata says `V14.0.9.0.TKLINXM` (MIUI 14.0.9 base), but payload likely contains HyperOS 3.0 images
- Same partition layout as stock (rosemary device)

---

## 3. Porting Process

### Step 1: Extract both ROMs

```bash
# Extract zip contents
unzip miui_ROSEMARYIDGlobal_V14.0.5.0.TKLIDXM_*.zip -d stock/
unzip rosemary_global-hybrid_full-OS3.0.303.0.WNTMIXM_*.zip -d port/

# Extract payload.bin from each using payload-dumper-go
payload-dumper-go -p all stock/payload.bin -o stock/images/
payload-dumper-go -p all port/payload.bin -o port/images/
```

### Step 2: Port the Kernel (boot.img)

**Use the STOCK ROM's kernel.** Do NOT use the port ROM's boot.img.

```bash
# Extract both boot images
unpack_bootimg --boot_img=stock/images/boot.img --out=stock/boot/
unpack_bootimg --boot_img=port/images/boot.img --out=port/boot/

# Keep stock kernel, merge port ramdisk for Android 16 init
cp stock/boot/kernel port/boot/
# Or rebuild from kernel source if needed
```

**Why:** Your device's kernel has the correct drivers for your specific panel, touch, sensors, and battery. The port ROM's kernel (if different) will likely cause boot failures.

**Ramdisk strategy:**
- Keep `init` and core Android 16 init scripts from port
- Replace device-specific `.rc` files from stock: `init.mt6785.rc`, `fstab.mt6785`, `ueventd.mt6785.rc`
- If using GKI: keep the GKI kernel from port but add your device's kernel modules from stock `vendor/lib/modules/`

### Step 3: Port Vendor Partition

This is the most critical step — the vendor partition contains all your device's HALs, firmware, and proprietary blobs.

**Strategy:** Copy stock vendor entirely, then selectively overlay port vendor files.

```bash
# Mount both vendor images
simg2img stock/images/vendor.img stock_vendor.img
simg2img port/images/vendor.img port_vendor.img
mkdir stock_v port_v
sudo mount -o loop stock_vendor.img stock_v
sudo mount -o loop port_vendor.img port_v
```

**What to KEEP from stock vendor (YOUR device):**

| Path | Purpose |
|------|---------|
| `vendor/firmware/` | ALL firmware (WiFi, BT, mcu, DSP) — NEVER replace |
| `vendor/firmware_mnt/` | Mounted firmware partition |
| `vendor/etc/init/hw/` | MT6785 hardware init scripts |
| `vendor/etc/permissions/` | Device permissions |
| `vendor/etc/sensors/` | Sensor configurations |
| `vendor/etc/wifi/` | WiFi config |
| `vendor/etc/.tp/` | Touch panel firmware |
| `vendor/lib/hw/` | Hardware abstraction layers |
| `vendor/lib64/hw/` | 64-bit HALs |
| `vendor/lib/libcam*` | Camera blobs (MTK-specific) |
| `vendor/lib64/libcam*` | 64-bit camera blobs |
| `vendor/lib/libmtk*` | MediaTek core libraries |
| `vendor/lib64/libmtk*` | 64-bit MTK libraries |
| `vendor/lib/libaudio*` | Audio DSP libraries |
| `vendor/lib64/libaudio*` | 64-bit audio libraries |
| `vendor/bin/` | Device-specific binaries |
| `vendor/radio/` | Modem/radio files |
| `vendor/build.prop` | Device properties (merge carefully) |
| `vendor/overlay/` | RRO overlays |

**What to use from PORT vendor (where newer/different):**
- `vendor/etc/audio_*` — newer audio policy configs (if compatible)
- `vendor/etc/media_codecs*.xml` — codec configs
- `vendor/lib/hw/gralloc.*` — graphics HAL (if G76 compatible)
- `vendor/lib64/hw/gralloc.*` — 64-bit graphics HAL
- `vendor/etc/vintf/` — VINTF manifest (merge)

**Checklist for critical vendor files:**
```
□ vendor/firmware/*        — stock ONLY
□ vendor/etc/fstab.mt6785 — stock ONLY  
□ vendor/lib/hw/*.so       — compare and test each
□ vendor/lib64/hw/*.so     — compare and test each
□ vendor/build.prop        — merge, keep device-specific props
□ vendor/overlay/*         — stock ONLY
□ vendor/radio/*           — stock ONLY
```

### Step 4: Merge build.prop

Start with port ROM's build.prop, then add/replace these device-specific properties from stock:

```properties
# Device identification (MUST match your device)
ro.product.board=rosemary
ro.product.name=rosemary
ro.product.device=rosemary
ro.product.model=M2101K7BG   # your specific model
ro.build.product=rosemary
ro.product.vendor=rosemary

# MediaTek platform
ro.mediatek.platform=MT6785
ro.mediatek.chip_ver=S_
mediatek.wlan.chip=CONSYS_MT6785

# Display panel
persist.vendor.dfps.level=60
ro.vendor.display.paneltype=2
ro.vendor.display.default_fps=60

# Audio
ro.vendor.audio.soundfx.type=mtk
persist.vendor.audio.mic_switch=1

# Camera
ro.vendor.camera.isp_mgr=1
ro.vendor.camera.fdvt.enable=1
```

### Step 5: Firmware (NEVER replace)

These are bootloader-level and **signed** by Xiaomi/MediaTek. Wrong firmware = hard brick.

```
preloader_raw  → stock ONLY
lk             → stock ONLY
tee            → stock ONLY
md1img         → stock ONLY
scp            → stock ONLY
spmfw          → stock ONLY
sspm           → stock ONLY
gz             → stock ONLY
audio_dsp      → stock ONLY
cam_vpu*       → stock ONLY
```

### Step 6: Disable Verified Boot (vbmeta)

Use the port ROM's vbmeta but disable verification:

```python
# Python one-liner
data = bytearray(open('port/images/vbmeta.img', 'rb').read())
data[123] |= 0x03  # DISABLE_VERITY | DISABLE_VERIFICATION
open('port/images/vbmeta_disabled.img', 'wb').write(data)
```

### Step 7: Assemble Flashable Package

**Option A: Fastboot (using FBFlasher from port ROM)**

```
images/
├── boot.img          ← your ported kernel
├── vendor.img        ← your merged vendor
├── system.img        ← port ROM's system
├── system_ext.img    ← port ROM's system_ext
├── product.img       ← port ROM's product
├── vbmeta.img        ← disabled verification
├── dtbo.img          ← stock
├── preloader_raw.bin ← stock
├── lk.img            ← stock
├── tee.img           ← stock
├── md1img.img        ← stock
├── scp.img           ← stock
└── ... other firmware from stock

Then run: ./FBFlasher-L.sh (Linux) or FBFlasher.bat (Windows)
```

**Option B: Recovery flashable zip**

Repack everything into a zip with:
```
META-INF/com/android/metadata       ← update build fingerprint
META-INF/com/google/android/         ← update-binary from port ROM
  update-binary
payload.bin                          ← regenerated with your modified images
```

Repack payload.bin from images:
```bash
# Use delta_generator or compatible tool
delta_generator --out_file=payload.bin --partition_names=system,vendor,boot,... --partition_images=system.img,vendor.img,boot.img,...
```

---

## 4. Common Issues & Fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bootloop at logo | Wrong kernel | Restore stock boot.img |
| Fastboot loop | Wrong vbmeta | Re-flash with disabled verification |
| No touchscreen | Wrong panel firmware | Restore stock `vendor/etc/.tp/` |
| No WiFi/BT | Missing firmware | Copy stock `vendor/firmware/wlan/` and `vendor/firmware/bt/` |
| No sound | Audio HAL mismatch | Copy stock `vendor/lib{64}/hw/audio.*` |
| Camera crashes | Camera blob mismatch | Copy ALL stock `libcam*` and `libmtk*` |
| No cellular | Bad modem firmware | Restore stock `md1img` completely |
| Very slow boot | SELinux denials | Set `androidboot.selinux=permissive` in kernel cmdline for testing |

**Debugging commands:**
```bash
# Kernel log
adb shell dmesg > dmesg.log

# Logcat
adb logcat -b all > logcat.log

# SELinux
adb shell getenforce
adb shell setenforce 0   # permissive for debugging
adb shell dmesg | grep "avc: denied"

# Partition table
adb shell ls -la /dev/block/by-name/
```

---

## 5. Key Porting Principles

1. **Kernel** — always from stock (your device's drivers)
2. **Firmware** — always from stock (signed, never cross-flash)
3. **Vendor blobs** — mostly from stock (MTK HALs are device-specific)
4. **System/Product** — mostly from port (Android/HyperOS framework)
5. **Vbmeta** — disable verification always
6. **Incremental testing** — change one thing at a time, test boot

---

## 6. Tools You'll Need

| Tool | Purpose |
|------|---------|
| [payload-dumper-go](https://github.com/ssut/payload-dumper-go) | Extract payload.bin → .img files |
| [Android Image Kitchen](https://forum.xda-developers.com/t/3389108/) | Unpack/repack boot.img |
| `simg2img` (part of android-tools) | Convert sparse → raw images |
| `lzma` / `xz` tools | Compress/decompress XZ streams |
| `adb` and `fastboot` | Flash and debug |
| Linux environment | Required for mounting ext4 images |

---

## 7. References

- [XDA: Redmi Note 10S Development](https://xdaforums.com/f/redmi-note-10s.12317/)
- [Device Tree: rosemary](https://github.com/windowz414/android_device_redmi_rosemary)
- [Xiaomi Kernel Source](https://github.com/MiCode/Xiaomi_Kernel_OpenSource)
- [LineageOS for rosemary](https://github.com/LineageOS/android_device_xiaomi_rosemary)
- [delta_generator (AOSP)](https://android.googlesource.com/platform/system/update_engine/)

---

*Generated from direct analysis of stock MIUI 14.0.5.0.TKLIDXM and port HyperOS 3.0.303.0 ROMs.*
