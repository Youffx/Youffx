# SukiSU 4.19 Kernel Patches

Compatibility patches for building [SukiSU Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) on 4.19 Linux kernels.

---

## Overview

SukiSU Ultra targets GKI and newer kernels by default. On 4.19 kernels, several incompatibilities arise from missing API wrappers, version-guarded functions, and ABI differences. This repository provides the necessary patches to resolve these issues.

### What's Included

| File | Type | Description |
|:-----|:-----|:------------|
| [`ksu_hooks_sukisu_4.19.patch`](ksu_hooks_sukisu_4.19.patch) | Official | Kernel source hooks from [SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch/tree/main/4.19) |
| [`sukisu-4.19-fix.patch`](sukisu-4.19-fix.patch) | All-in-one | Module compatibility fixes + kernel source hooks |

### Compatibility Matrix

| Kernel Version | Module Fixes | Kernel Hooks | Status |
|:---------------|:-------------|:-------------|:-------|
| 4.19.x | Required | Required | Fully Supported |
| 5.4.x | Required | Partial | Supported |
| 5.10.x+ | Not Required | Not Required | Natively Supported |

---

## Prerequisites

- A 4.19-based kernel source tree
- `SukiSU-Ultra` module installed via the official setup script
- `python3` (for the all-in-one patch)
- Standard build tools (`gcc`, `make`, `sed`)

---

## Quick Start

```bash
# 1. Clone your kernel source
git clone --depth=1 --branch <your_branch> <your_kernel_repo> kernel
cd kernel

# 2. Run the SukiSU setup script
curl -LSs https://raw.githubusercontent.com/SukiSU-Ultra/SukiSU-Ultra/builtin/kernel/setup.sh | bash -s builtin

# 3. Apply the compatibility patch
sh /path/to/sukisu/sukisu-4.19-fix.patch
```

> **Note:** The patch must be applied **after** the SukiSU setup script, as it modifies files created by that script.

---

## Manual Installation

If you prefer to apply patches individually or need to debug specific issues, follow the steps below.

### Step 1 -- KernelSU Module Fixes

These `sed` commands fix API incompatibilities in the KernelSU module source.

<details>
<summary><strong>Click to expand sed commands</strong></summary>

```bash
# Guard selinux_hide function calls (only available in kernel >= 5.10)
sed -i 's/    ksu_selinux_hide_handle_post_fs_data();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n    ksu_selinux_hide_handle_post_fs_data();\n#endif/' \
    KernelSU/kernel/runtime/ksud.c

sed -i 's/            ksu_selinux_hide_handle_second_stage();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n            ksu_selinux_hide_handle_second_stage();\n#endif/' \
    KernelSU/kernel/runtime/ksud.c

sed -i 's/                ksu_selinux_hide_handle_second_stage();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n                ksu_selinux_hide_handle_second_stage();\n#endif/' \
    KernelSU/kernel/runtime/ksud.c

# Fix USER_ARG_NULL: dereference pointer to match expected struct value
sed -i 's/#define USER_ARG_NULL user_arg_null_ptr()/#define USER_ARG_NULL (*user_arg_null_ptr())/' \
    KernelSU/kernel/sulog/event.c

# Fix app profile version mismatch (Manager v3 vs Kernel v4)
sed -i 's/int ksu_set_app_profile(struct app_profile \*profile)/static void migrate_profile(u32 version, struct app_profile *profile);\nint ksu_set_app_profile(struct app_profile *profile)/' \
    KernelSU/kernel/policy/allowlist.c

sed -i '/if (!profile_valid(profile)) {/i\    if (profile->version < KSU_APP_PROFILE_VER) {\n        migrate_profile(profile->version, profile);\n    }' \
    KernelSU/kernel/policy/allowlist.c
```

</details>

### Step 2 -- Kernel Source Hooks

Apply the official SukiSU 4.19 hook patch:

```bash
patch -p1 < ksu_hooks_sukisu_4.19.patch
```

This patches the following kernel source files:

| File | Hook Point | Purpose |
|:-----|:-----------|:--------|
| `fs/exec.c` | `do_execve` / `compat_do_execve` | Intercepts execve for su and ksud with 32-bit compat |
| `fs/open.c` | `SYSCALL_DEFINE3(faccessat)` | Intercepts faccessat for su path redirection |
| `fs/read_write.c` | `SYSCALL_DEFINE3(read)` | Intercepts VFS read for ksud communication |
| `fs/stat.c` | `newfstatat` / `fstatat64` | Intercepts stat for su path redirection (32-bit included) |
| `drivers/input/input.c` | `input_event` | Input event hook for key-based root trigger |
| `drivers/tty/pty.c` | `pts_unix98_lookup` | Devpts hook for terminal device handling |

---

## Patch Details

### KernelSU Module Fixes

| Issue | Root Cause | Fix |
|:------|:-----------|:----|
| `ksu_selinux_hide_handle_*` implicit declaration | Functions conditionally compiled only for `>= 5.10` | Wrap calls with `#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)` |
| `USER_ARG_NULL` type mismatch | Macro returns a pointer, but `ksu_sulog_capture` expects a struct by value | Dereference with `(*user_arg_null_ptr())` |
| App profile version mismatch | Manager app sends version `3`, kernel expects version `4` | Add `migrate_profile()` to auto-upgrade old profiles |

### Kernel Source Hooks

The official 4.19 patch provides hand-written kernel source hooks (as opposed to kprobes) for reliable symbol resolution on non-GKI kernels. Key features:

- **Dual exec path** -- Routes through `ksu_execveat_hook` flag to switch between ksud and sucompat
- **32-bit su support** -- Hooks `compat_do_execve` and `fstatat64` for 32-bit applications
- **Devpts interception** -- Ensures correct terminal device handling under root sessions

---

## Troubleshooting

<details>
<summary><strong>Error: <code>implicit declaration of function 'ksu_selinux_hide_handle_*'</code></strong></summary>

You skipped Step 1. The selinux_hide functions do not exist in 4.19 kernels. Apply the module fixes before building.

</details>

<details>
<summary><strong>Error: <code>passing 'struct user_arg_ptr *' to parameter of incompatible type</code></strong></summary>

The `USER_ARG_NULL` macro was not patched. Ensure you ran the `sed` command for `sulog/event.c`.

</details>

<details>
<summary><strong>Error: <code>failed to update app profile</code> in Manager</strong></summary>

The profile version migration patch is missing. Apply the `allowlist.c` fix so old profiles are auto-migrated.

</details>

<details>
<summary><strong>Error: <code>ksu_execveat_hook</code> undefined</strong></summary>

The kernel source hooks were not applied. Run `patch -p1 < ksu_hooks_sukisu_4.19.patch` from your kernel root.

</details>

---

## Credits

- [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) -- Main SukiSU project
- [SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch) -- Official 4.19 kernel hooks

---

## License

These patches are provided as-is for educational and development purposes. Refer to the [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra) license for terms regarding the base project.
