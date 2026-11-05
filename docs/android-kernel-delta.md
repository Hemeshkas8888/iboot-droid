# Android kernel delta: what Android needs from the kernel

Goal: **the Orchard `apple-16k` kernel stays as built; this tree adds only
the options Android needs on top.** Everything here is configuration, not
driver work. iBoot Droid carries no kernel fork in M0.

## What already exists in the kernel (verified in orchard's
`kernel/configs/apple-16k/config` at orchard `a6ffc904`)

`CONFIG_ANDROID_BINDER_IPC=y` — the IPC core Android needs. Also already
right for Android: `SECCOMP(_FILTER)`, `TMPFS_XATTR`, `DEVTMPFS`,
namespaces, `CGROUPS` (+PERF/PIDS/HUGETLB/DEVICES), `PSI`, `EXT4_FS_SECURITY`,
`OVERLAY_FS`, `USB_CONFIGFS_F_FS` (adb's functionfs), `PSTORE_RAM`, the
ARM64-CE crypto set, cgroup-v2 `CGROUP_WRITEBACK`.

## What the fragment turns on (`kernelspace/android-binder.cfg`)

| Option | Why Android needs it |
|---|---|
| `CONFIG_ANDROID_BINDERFS=y` | Android 15/16 GSIs mount `/dev/binderfs` from `init` (`fstab.hardware`/init.rc); binder pseudo-devices are created there, not hardcoded. Without it the GSI's `mount binder binder /dev/binderfs none` step fails and services (incl. `servicemanager`) die. |
| `CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder` | Legacy default names; harmless under binderfs, keeps non-Android shells useful. |
| `CONFIG_SECURITY_SELINUX=y` (+`DEVELOP=y`) | Android `init` hard-requires SELinux support and mounts `sys/fs/selinux`; GSI policy ships in `system.img`. The config's `LSM="landlock,selinux"` already names selinux — this flips the module on so that entry is honoured. `DEVELOP=y` allows the lab-mode `setenforce 0` during bring-up (M3 logcat); it is expected to be disabled before any "release" claim. |
| `CONFIG_CGROUP_FREEZER=y` | Android's freeze-based app lifecycle (`cgroup.freeze`) hangs without the controller; ActivityManager uses it from Android 12+. Not part of the binder story but comes free at M3. |

Not added (still optional): `F2FS_FS` (userdata can be ext4 first),
`DMABUF_HEAPS` (gralloc can use `udmabuf`, already `=y`), `ZRAM`
(zswap+zstd is already default-on; zram lands when we tune swap in M3/M4),
`CGROUP_BPF` (only needed for some networking features; add with tests when
an app calls for it). Each would be one more fragment line in this file, not
a kernel fork.

## How it is applied at build time

The fragment is merged into the platform config inside the container using
the kernel tree's own `scripts/config` and the same `make olddefconfig` flow
`kernel/configs/apple-16k/README.md` documents:

```sh
cp <orchard>/kernel/configs/apple-16k/config .config
python3 scripts/config --file .config \
  --set-val ANDROID_BINDERFS y \
  --set-str ANDROID_BINDER_DEVICES binder,hwbinder,vndbinder \
  --set-val SECURITY_SELINUX y
make LLVM=-19 ARCH=arm64 olddefconfig
```

The fragment file exists so the delta is reviewable as data and so the
eventual orchard PR has its exact content offline. The orchard change that
flips these is a one-line-per-option patch to
`kernel/configs/apple-16k/config`; iBoot Droid ships no patched kernel
binary in the meantime.

## Verification plan (retire the assumption "binder works")

- Build check (M2): after `olddefconfig`, assert `CONFIG_ANDROID_BINDERFS=y`
  is present and `make ARCH=arm64 Image` succeeds.
- Device check (M2/M3): after `mount binder binder /dev/binderfs none`,
  `ls /dev/binderfs` must list `binder`, `hwbinder`, `vndbinder`;
  `servicemanager` starts without the mount. Record both outcomes in
  docs/KNOWN-ISSUES.md; a boot not reaching `sys.boot_completed` is a
  failure, not a demo.
