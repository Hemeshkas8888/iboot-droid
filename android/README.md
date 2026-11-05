# iBoot Droid vendor layer

Everything Android needs that no vendor image exists for on this device,
generated in-repo and reproducibly (no container, no network).

Layers, mirroring the forks' role map:

- `vendor/`: the vendor layer proper — `fstab`, `init.rc`s, `ueventd.rc`,
  VINTF manifests, SELinux placeholder. Install writes it next to the GSI.
- `gsi.json`: the pinned official AOSP GSI (vanilla `aosp_arm64-exp` builds)
  with SHA-256, fetched at install/runtime by `fetch-gsi`, never committed.
- `build-vendor`: producer for the `android-vendor` component (same keyed
  scheme as every other component; see the fork's tools/components.py).

## Boot handoff (M2/M3 design note)

The chain stays: palera1n/checkm8 → Pongo → m1n1 → orchard kernel + orchard
initrd (boot contract, `root=PARTUUID=`). iBoot Droid changes only the
**last hop**: the boot entry's `options` carry `init=/init` so the orchard
initrd's `switch_root /newroot /init` execs Android's first-stage init from
the root partition, which holds an unpacked system-as-root GSI layout plus
this vendor layer. First-stage init find `fstab` at
`first_stage_mount`'s fallback locations; this vendor layer's `fstab`
targets partitions created by the installer (PARTUUID placeholders
substituted at install; same rules as the boot contract: identity by
PARTUUID, never by partition number).

adb is off by default (`init.usb.configfs` default); `orchard logcat
--enable-adb` is an explicit opt-in that a UI confirmation must accept.
No root shell, no passwordless sudo, no auto-login.

## Milestones this directory maps to

- M2: kernel fragment (`kernelspace/android-binder.cfg`), this vendor layer
  in the release, GSI on the root partition, `getconf PAGE_SIZE` == 16384,
  and the ELF alignment sweep as the 16K proof.
- M3: `logcat` over adb (opt-in) with a black screen accepted as success.
- M4: software SurfaceFlinger over the `adbe` DRM KMS driver.
