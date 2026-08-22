#!/usr/bin/env python3
"""Apply KernelSU manual hooks to kernel source for 4.19."""
import os, sys, re

def patch_file(path, patches):
    """Apply list of (old, new) replacements to file."""
    with open(path, 'r') as f:
        content = f.read()
    for old, new in patches:
        if old not in content:
            print(f"  WARNING: pattern not found in {path}:")
            print(f"    {old[:80]}...")
            return False
        content = content.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  Patched {path}")
    return True

def main():
    ks = "#ifdef CONFIG_KSU\nextern void ksu_handle_sys_read(unsigned int fd);\n#else\nstatic inline void ksu_handle_sys_read(unsigned int fd) {}\n#endif"
    kf = "#ifdef CONFIG_KSU\nextern void ksu_handle_sys_fstat(unsigned int fd, struct kstat *stat);\n#else\nstatic inline void ksu_handle_sys_fstat(unsigned int fd, struct kstat *stat) {}\n#endif"
    ki = "#ifdef CONFIG_KSU\nextern int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value);\n#else\nstatic inline int ksu_handle_input_handle_event(unsigned int *type, unsigned int *code, int *value) { return 0; }\n#endif"
    kr = "#ifdef CONFIG_KSU\nextern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user *arg);\n#else\nstatic inline int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd, void __user *arg) { return 0; }\n#endif"

    ok = True

    # fs/read_write.c
    ok &= patch_file("fs/read_write.c", [
        ('#include "internal.h"\n\n#include <linux/uaccess.h>',
         '#include "internal.h"\n#include <linux/module.h>\n\n' + ks + '\n\n#include <linux/uaccess.h>'),
        ('ssize_t ksys_read(unsigned int fd, char __user *buf, size_t count)\n{\n\tstruct fd f = fdget_pos(fd);',
         'ssize_t ksys_read(unsigned int fd, char __user *buf, size_t count)\n{\n\tksu_handle_sys_read(fd);\n\tstruct fd f = fdget_pos(fd);'),
    ])

    # fs/stat.c
    ok &= patch_file("fs/stat.c", [
        ('#include <linux/uaccess.h>\n#include <asm/unistd.h>\n\n/**',
         '#include <linux/uaccess.h>\n#include <asm/unistd.h>\n#include <linux/module.h>\n\n' + kf + '\n\n/**'),
        ('SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)\n{\n\tstruct kstat stat;\n\tint error = vfs_fstat(fd, &stat);\n\n\tif (!error)',
         'SYSCALL_DEFINE2(newfstat, unsigned int, fd, struct stat __user *, statbuf)\n{\n\tstruct kstat stat;\n\tint error = vfs_fstat(fd, &stat);\n\tksu_handle_sys_fstat(fd, &stat);\n\n\tif (!error)'),
    ])

    # drivers/input/input.c
    ok &= patch_file("drivers/input/input.c", [
        ('#include "input-compat.h"\n\nMODULE_AUTHOR',
         '#include "input-compat.h"\n#include <linux/module.h>\n\n' + ki + '\n\nMODULE_AUTHOR'),
        ('static void input_handle_event(struct input_dev *dev,\n\t\t\t       unsigned int type, unsigned int code, int value)\n{\n\tint disposition = input_get_disposition',
         'static void input_handle_event(struct input_dev *dev,\n\t\t\t       unsigned int type, unsigned int code, int value)\n{\n\tksu_handle_input_handle_event(&type, &code, &value);\n\tint disposition = input_get_disposition'),
    ])

    # kernel/reboot.c
    ok &= patch_file("kernel/reboot.c", [
        ('#include <linux/uaccess.h>\n\n/*\n * this indicates whether',
         '#include <linux/uaccess.h>\n#include <linux/module.h>\n\n' + kr + '\n\n/*\n * this indicates whether'),
        ('SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n\t\tvoid __user *, arg)\n{\n\tstruct pid_namespace *pid_ns',
         'SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n\t\tvoid __user *, arg)\n{\n\tif (ksu_handle_sys_reboot(magic1, magic2, cmd, arg))\n\t\treturn 0;\n\tstruct pid_namespace *pid_ns'),
    ])

    if ok:
        print("[+] All patches applied successfully.")
    else:
        print("[!] Some patches failed. Check warnings above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
