# SukiSU 4.19 Kernel Patches

Patches for building SukiSU on 4.19 kernels.

## Files

| File | Description |
|------|-------------|
| `ksu_hooks_sukisu_4.19.patch` | Official SukiSU 4.19 kernel hooks (exec, stat, pty) from [SukiSU_patch](https://github.com/SukiSU-Ultra/SukiSU_patch/blob/main/4.19/ksu_hooks_sukisu_4.19.patch) |
| `sukisu-4.19-fix.patch` | Full compatibility patch (module fixes + kernel hooks) |

## How to Apply

### Option A: Using the full fix patch (recommended)

Run after SukiSU setup script:

```bash
cd kernel
curl -LSs https://raw.githubusercontent.com/SukiSU-Ultra/SukiSU-Ultra/builtin/kernel/setup.sh | bash -s builtin
sh /path/to/sukisu-4.19-fix.patch
```

This applies both KernelSU module fixes and official 4.19 kernel hooks automatically.

### Option B: Manual application

#### 1. KernelSU module fixes (required)

The SukiSU module requires these fixes for 4.19 compatibility:

```bash
# Guard selinux_hide calls (only included for >=5.10)
sed -i 's/    ksu_selinux_hide_handle_post_fs_data();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n    ksu_selinux_hide_handle_post_fs_data();\n#endif/' KernelSU/kernel/runtime/ksud.c
sed -i 's/            ksu_selinux_hide_handle_second_stage();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n            ksu_selinux_hide_handle_second_stage();\n#endif/' KernelSU/kernel/runtime/ksud.c
sed -i 's/                ksu_selinux_hide_handle_second_stage();/#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)\n                ksu_selinux_hide_handle_second_stage();\n#endif/' KernelSU/kernel/runtime/ksud.c

# Fix USER_ARG_NULL pointer dereference
sed -i 's/#define USER_ARG_NULL user_arg_null_ptr()/#define USER_ARG_NULL (*user_arg_null_ptr())/' KernelSU/kernel/sulog/event.c

# Fix app profile version mismatch (Manager sends v3, kernel expects v4)
sed -i 's/int ksu_set_app_profile(struct app_profile \*profile)/static void migrate_profile(u32 version, struct app_profile *profile);\nint ksu_set_app_profile(struct app_profile *profile)/' KernelSU/kernel/policy/allowlist.c
sed -i '/if (!profile_valid(profile)) {/i\    if (profile->version < KSU_APP_PROFILE_VER) {\n        migrate_profile(profile->version, profile);\n    }' KernelSU/kernel/policy/allowlist.c
```

#### 2. Official 4.19 kernel hooks

Apply the official patch for kernel source files:

```bash
patch -p1 < ksu_hooks_sukisu_4.19.patch
```

This hooks the following files:
- `fs/exec.c` - execve with ksu_execveat_hook branching + 32-bit compat
- `fs/open.c` - faccessat
- `fs/read_write.c` - vfs_read
- `fs/stat.c` - newfstatat + fstatat64 (32-bit)
- `drivers/input/input.c` - input_event
- `drivers/tty/pty.c` - devpts

## What Each Fix Does

| Fix | Problem | Solution |
|-----|---------|----------|
| `selinux_hide` guard | Functions only exist in kernel >=5.10 | Wrap calls with `LINUX_VERSION_CODE` check |
| `USER_ARG_NULL` | Returns pointer, but caller expects value | Dereference with `(*user_arg_null_ptr())` |
| `migrate_profile` | Manager sends profile version 3, kernel expects 4 | Auto-migrate old profiles to current version |
| `exec.c` hooks | su compatibility needs execve interception | Hook `do_execve` + `compat_do_execve` for 32-bit |
| `fstatat64` hook | 32-bit su path not intercepted | Add stat hook for `fstatat64` syscall |
| `pty.c` devpts | Terminal device handling under su | Hook `pts_unix98_lookup` for devpts |
