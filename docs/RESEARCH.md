# iBoot Droid research

Status: **M0 (research step, no Android code yet).** Every hardware or
behaviour claim below is tagged:

- **VERIFIED** — read directly from the file/page named next to it.
- **ASSUMED** — believed but not proven; each carries the test that will
  retire it.

Upstream commit hashes are those of shallow clones taken 2026-11-05. Upstream
history is never rewritten upstream; this tree is a fork of omarchy-a at the
hash above.

## 1. Upstreams: role, license, reuse

| Repo | Role | Commit (2026-11-05) | License | Reuse decision |
|---|---|---|---|---|
| OrchardLinux/omarchy-a | Fork base: boot scripts, installer, release format, CI, tests | `bb08039d68f57885a951d32bac44188fcb8d10ed` | GPL-2.0-or-later (`LICENSE`) | Reuse structure entirely; replace the Arch/Omarchy userland with Android |
| OrchardLinux/orchard | Hardware, kernel, device trees, firmware recipes, host CLI, recovery runtime, boot contract. (Formerly `hardware`; the CLI repo `OrchardLinux/cli` was **merged into it** and is archived) | `a6ffc904bf8acb7af2fd0fc94f84ca194bd82ed2` | GPL-2.0-or-later; third-party under `LICENSES/` (m1n1, PongoOS, wireless-regdb) | Consume as upstream; fork only what we must change (kernel config fragment for Android) |
| OrchardLinux/cli | Archived host CLI, superseded by orchard | `07b9c6c3c4d27e2e0e13b44a0fe34e4d8c7cf7ed` | GPL-2.0-or-later | Reference only; `orchard` handles launch/install/logcat |
| OrchardLinux/resize-apfs | APFS shrink to make room | `ac1658923378dcb800523d7dcd45002fc2bc5862` | MIT (`LICENSE`) | Reuse as-is, referenced from our installer |
| OrchardLinux/minimal-linux | Template for a non-Arch "remix" on the same release format | `e9c4f251aaa55a285032e7edd52b27776d4dbac3` | GPL-2.0-or-later (`LICENSE`) | imitate its `system/build_base.py`, release audit and component cache model for the Android image |
| corellium/projectsandcastle | Prior art: Android on A10 via checkm8 | read 2026-11-05, `master` README | see §7 | Idea reuse only until per-repo licenses are recorded; credited in NOTICE |

Kernel/firmware facts quoted from orchard were re-checked in the orchard tree
at the hash above; where this document says "kernel/...", the path is inside
orchard.

Kernel version family and base: **Linux `7.3.0-rc1`** (base
`torvalds/linux@c ee9395a` recorded in `kernel/sources.toml`; catalog name
`7.3.0-rc1-orchard-apple-16k`, VERIFIED in `tools/catalog/drivers.json`) with
A7–A11 platform support imported from **HoolockLinux** (Nick Chan's staging
tree, `kernel/patches/hoolock/`, status `integrated`) plus device work formed
by the `pauli1go` import series and `devices/` patches.

## 2. Boot path, DFU → userland (how-it-works, as implemented)

Chain, **VERIFIED** (`orchard/docs/boot-contract.md`,
`omarchy-a/docs/how-it-works.md`, `orchard/boot/initramfs/root/init`):

```text
Host: orchard launch
  └─ palera1n / checkm8 (BootROM exploit, DFU)
       └─ PongoOS
            └─ m1n1 (orchard's patches; splash + boot manager)
                 └─ Linux kernel + initrd + DTB (BLS entry from XBOOTLDR)
                      └─ orchard initrd: mounts root=PARTUUID=, switch_root
                           └─ /sbin/init (the OS takes over)
```

Details that constrain the Android port:

- **Boot storage is read** by m1n1, not the host. `orchard launch` sends
  `P_BOOT_ENTRIES`/`P_BOOT_START` (`0x1500`–`0x1502`, orchard-local ops
  0007–0009); m1n1 parses BLS Type #1 entries on a single **XBOOTLDR**
  (`bc13c2ff-…`) FAT32 boot partition, applies ADT fill-ins (MAC addresses,
  calibration, memory, CPUs) to the kernel DTB, paints the splash, shuts down
  storage and boots. Boot is tethered: every cold start needs the host.
- **Storage init is one-shot per m1n1 session on A10**: a second
  `P_MAIN_STORAGE_INIT` hangs (J71b, 2026-11-01, boot-contract "Host and
  m1n1"). **VERIFIED.** Android must not depend on reboot-time re-initialisation
  by the host path; large storage writes at runtime belong to the kernel ANS
  driver, not the bootloader.
- **The installed initrd is a fixed, tiny script**
  (`orchard/boot/initramfs/root/init`): parses `root=PARTUUID=/rootfstype=/
  rootflags=/ro|rw/init=` from the BLS entry's `options`, loads the storage
  modules listed in `/etc/orchard/modules`, waits up to 30 s for the partition,
  mounts it read-only-or-rw, sets up the USB gadget (NCM + ACM, serial
  `BOARD:<profile>`), then `switch_root /newroot $init`.
- **The Android hand-off point is exactly `exec switch_root /newroot init=`.**
  Android first-stage init needs to be PID 1: we set `init=/init` in the boot
  entry (BLS `options`) and the root partition starts with Android's
  `/init`. The vendor layer's `fstab`/first-stage mounts are passed via
  device-tree-independent channels (cmdline `androidboot.*`); full design in
  M2, with a smoke test that boots Android init from the *first* partition
  boot.
- Recovery/`orchard-device` runtime (`bootstrap` over USB serial, storage
  fence) is shared by all devices and stays untouched.

## 3. What the release/install flow gives us (verified, reused)

From `omarchy-a` (forked) + `orchard`:

- Release artifacts and verification: `index.toml` pins `release.toml`; every
  artifact carries size + SHA-256 (`omarchy-a/docs/how-it-works.md`,
  `release/manifests.py`). We add manifest fields: `gsi_track`, `page_size`,
  `kernel_version`, `vendor_layer_hash`.
- Install lifecycle: make room with resize-apfs (never shrinks iPadOS itself
  from the tethered installer) → boot recovery → SSH-over-USB-serial key
  provisioning → plan (partition inspection; typed confirmation before
  replacing a Linux install) → write boot + root partitions → boot via m1n1.
  **VERIFIED** (`how-it-works.md` §Installation lifecycle,
  `resize-apfs/README.md`; the APFS shrink is hardware-tested on J71b only —
  treat J171 as untested until run: **ASSUMED**, tested in M2 on hardware).
- Partition layout (GPT, DPS): one XBOOTLDR boot partition + one root
  partition per system, iPadOS container untouched besides the agreed resize.
  Android root partition can hold `system.img`-like content natively; exact
  split (system / vendor / userdata as 1 partition with subdirs vs 3
  partitions) is an M2 decision needing VINTF/dm-verity trade-offs.

## 4. iPad 7 (J171/J172) — what already exists (driver inventory)

Board identity, **VERIFIED** (`orchard/devices/j171/device.toml`, `j172`):

- iPad 7 Wi-Fi = `iPad7,11` = **J171**, `dt_compatible` includes `apple,j171`;
  BDID/chip match `chip=0x8010` (A10/T8010) `board=0x1c`.
- iPad 7 Cellular = `iPad7,12` = **J172**, `board=0x1e`.
- Boot method: `checkm8-pongo` (same as iPad 6). No published j171 installer
  release yet (device.toml says the j71b URL pattern mirrors).
- j171a/j172a are iPad 8 (A11-class, T8020) and are *not* brought up
  (`devices/j171a/device.toml`: no bring-up) — out of scope.

### 4.1 Feature state per device (from device.toml [features])

Feature vocabulary/fn (verified in `features.toml`, `devices/j171/device.toml:36`,
`devices/j172/device.toml:36`):

**J171 (iPad 7 Wi-Fi) — status `experimental`:**

| Feature | State | Driver behind it |
|---|---|---|
| display | **working** | `drm-adbe` (Apple display pipe KMS) + t8010 display DT (`kernel/patches/devices/t8010/0010`, `0015`); simplefb fallback path exists via loader framebuffer |
| backlight | **working** | `apple_dwi` (`kernel/patches/drivers/backlight/0001`) |
| touch | **working** | `apple_z2` touchscreen over SPI; in-tree J172 (`kernel/patches/import/pauli1go/0013/0015`) plus both-iPad-7 variant name (`input/0017`); T8010 touch clock (`drivers/clk/0001-0004`); T8010 touch SPI wiring in `t8010-ipad7.dtsi`; runtime module built out-of-tree per kernel README (`CONFIG_TOUCHSCREEN_APPLE_Z2` disabled there; runtime driver `j71b_z2.ko`) — the in-tree `apple_z2` patch set carries iPad 7 (ASSUMED→verify which module form ships for j171: build test M1) |
| buttons | **working** | GPIO/pinctrl + PMIC GPIO via `d2365` (`drivers/gpio/0001-0005`) |
| storage_read/write | **working** | Apple ANS NVMe: `nvme-pci-apple-ans` fixes (`drivers/nvme/0001`, `drivers/pci/0008-0011`) + FlatDMA support from pauli1go 0003; T8010 PCIe host `pauli1go 0001/0002`; DART2 (`pauli1go 0064`) |
| wifi | **working** | `brcmfmac` (BCM4355C1 / "ruddera/b" PCIe) + `pci-pwrctrl-apple-wifi` sequencing + `PCI apple h9p` host-bridge port lifecycle (`pauli1go 0045-0048`, `devices/t8010` patches for Wi-Fi port) + SIO SmartIO (`t8010-smartio.bin` firmware from kernelcache) |
| battery | **working** | BQ27545 HDQ gauge over UART-HDQ (`w1`-uart, `drivers/power/0001`, `import/pauli1go 0024-0029`) + D2365 charger + Bellatrix source (`drivers/power/0003-0014`) |
| accelerometer | untested | AOP (Always-On-Processor) accelerator via A7-IOP mailbox (`drivers/iio/0004`, `devices/t8010/0007`, `soc-apple/0006-0009`) |
| light_sensor | untested | tsl2583 + Apple CT819 variants (`drivers/iio/0001-0003`, `pauli1go 0114-0117`) |
| gyroscope | missing | none in tree |
| touch_id | missing | none (Home button sensor; not required) |
| bluetooth_* | **missing** | pairing works on the iPad 6 Kernel Series but the J171/J172 HCD recipe exists (`devices/j171/firmware.json`: `BCM.apple,j171-MUR.hcd` + `USI` extracted by `bluetool-hcd` from BlueTool) and `hci_bcm` BCM4355C1 support is in (`pauli1go 0056-0059`); needs runtime bring-up |
| charging | untested→piece-meal working | D2365 charger grants 500 mA (J171 README, PR #46); >500 mA needs PMU event line work; charge control missing |
| suspend/resume | untested | cpuidle driver exists (`drivers/cpuidle/0001`) |
| audio_* | missing | ASoC MCA/CS42L81 + max98357a are in-tree for j71b (iPad 6 speaker chain, `drivers/sound/*`); iPad 7 needs board wiring work |
| usb_serial/network | untested | DWC2 + configfs gadget proven on J71b |
| camera | missing/none | not attempted |

**J172 (iPad 7 Cellular)** — same `t8010-ipad7.dtsi`; every feature state is
"untested" in device.toml (never bench-locked); cellular modem missing. The
shared-DTS structure is **VERIFIED** (`devices/t8010/0001` commit message: iPad 6
(iPad7,5/iPad7,6) and iPad 7 (J171/J172) share the Wi-Fi PCIe port + Wi-Fi
regulator + platform control, PMIC GPIO controller, Bluetooth UART, HDQ gauge
UART and touchscreen SPI wiring).

### 4.2 What Android adds on top of the kernel (config deltas, all needed)

Current `kernel/configs/apple-16k/config` (VERIFIED grep at the hash above) —
present (good for Android):

`CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_EXT4_FS=y` + `EXT4_FS_SECURITY=y`,
`CONFIG_OVERLAY_FS=y`, `CONFIG_SQUASHFS=y`, `CONFIG_PSI=y`,
`CONFIG_CGROUPS=y (+PERF/PIDS/HUGETLB/DEVICES/CPUACCT/WRITEBACK/SCHED)`,
`CONFIG_FREEZER=y`, `CONFIG_SECCOMP(_FILTER)=y`, `CONFIG_CMA=y`,
`CONFIG_DEVTMPFS=y`, `CONFIG_KALLSYMS=y`, namespaces all `=y`,
`CONFIG_TMPFS_XATTR=y`, `CONFIG_KEYS=y`, AES/CTR-ARM64 CE crypto,
`CONFIG_USB_CONFIGFS_F_FS=y` (ADB functionfs), `CONFIG_SYNC_FILE=y`,
`CONFIG_PSTORE_RAM=y`, `CONFIG_TUN=y`, `CONFIG_DWC2=y`,
`CONFIG_FRAMEBUFFER_CONSOLE=y`, netfilter/nftables family present, zswap
(zstd) default on.

Absent and required for Android (**M2 kernel work items, not driver work**):

- `CONFIG_SECURITY_SELINUX` (+ `AUDIT_BPF`, `NET_CLS_CGROUP`, `IP_ADVANCED_ROUTER`) — the LSM string already names `selinux` but the security module is off.
- `CONFIG_ANDROID_BINDERFS` (currently hardcoded build requires binder devices; binderfs is the modern path and keeps this config boot-strappable for a GSI).
- `CONFIG_F2FS_FS` (+ crypto) for userdata; ext4 works but f2fs is the Android default on flash.
- `CONFIG_ZRAM` + `CONFIG_ZRAM_MULT_WRITEBACK` (zswap is not Android's swap path; keep both).
- `CONFIG_DMABUF_HEAPS` (+ `SYSTEM_HEAP`, `SYSTEM_WITH_CONSTRUCTION_HEAP`) — Android allocators; `CONFIG_UDMABUF=y` already set.
- `CONFIG_CGROUP_BPF`, `CGROUP_FREEZER` (Android slabs need them; PSI is already on).
- `CONFIG_LRU_GEN` (MGLRU) — off; fine initially (Android ships its own LMK path).

To be resolved by testing (ASSUMED→verify each in M2): frame buffer console
must yield cleanly to SurfaceFlinger (fbcon takeover off under Android init),
AOP IRQ sharing with iio, `t8010-smartio.bin` load order.

None of these change driver behaviour: they are configuration/infra work.
Call out: **no new Apple driver is required by Android that the Orchard tree
does not already have for iPad 7.**

### 4.3 GPU (bigger than assumed)

`kernel/patches/drivers/gpu/0001-drm-imagination-Support-the-Apple-A10-T8010-GPU.patch`
(**VERIFIED** for text, 3.5k lines added): the A10's GPU is a Rogue core
(`CORE_ID 0x011b0602`, BVNC 13.10.6.2) driven through Apple's own `GFX`
firmware on an RTKit coprocessor behind the A7-IOP mailbox, with devfreq,
runtime PM and an Apple firmware variant selected by `apple,t8010-gpu` /
`CONFIG_DRM_POWERVR_APPLE`.

The commit message reports hardware testing **on J71b (iPad 6)** at the time of
writing: Hyprland + Zink + "Mesa G9P" Vulkan at 60 fps with live blur, plus
an s2idle suspend/resume test. **VERIFIED** as a claim in-tree; nothing
on-disk identifies the Mesa fork's public URL → the **userspace** shard is
ASSUMED for now (research task: find/verify Mesa G9P publicly or plan
packaging it ourselves under NOTICE).

`features.toml`'s feature vocabulary has no `gpu` key; neither device.toml
records GPU state. Therefore:

- iBoot Droid treats GPU as **optional, Track-B-first**: software rendering
  (SwiftShader/llvmpipe-equivalent, software gralloc + hwcomposer) is the
  reference path for M4; a Vulkan-capable hwcomposer behind DRM
  (powervr DRM node) is a later experiment, gated behind a device.toml
  feature key we add.

Implication for the mission text ("PowerVR GT7600 Plus has no open driver"):
**that assumption is outdated for the kernel half of the GPU**; only the
userspace (Mesa side) is still open research.

## 5. Page size — verification and the 16K story

**The Orchard/Beaver iPad 7 kernel is already 16K.** `kernel/configs/apple-16k/config`
(VERIFIED):

```
CONFIG_ARM64_16K_PAGES=y
CONFIG_PAGE_SIZE_16KB=y
CONFIG_HAVE_PAGE_SIZE_16KB=y
CONFIG_ARM64_VA_BITS_48=y
# CONFIG_ARM64_4K_PAGES is not set
```

`apple-16k/README.md` documents its origin: resolved config derived from
`HoolockLinux/docs`' `config_16k` snapshot
`23ebe1fbc375599221553a7e1815e5de182a6b42` with Debian Clang/LLVM 19.1.7; a
4K sibling (`kernel/configs/apple-4k/`) exists for other targets or for
running 4K-built handcuffs.

Kernel `ARCH_MMAP_RND_*` and DART/no-dma setup already match an A10 running
with 16K pages.

Apple A-series using 16K pages — **VERIFIED** for this device family by the
same upstream evidence as §2/§5: orchard's iPad 6/iPad 7 bring-up runs Linux
with `CONFIG_ARM64_16K_PAGES=y` and NVMe/DART hardware that was
hardware-tested (J71b boot contract tests, j171 device.toml storage "working");
plus the AOSP 16 KB page doc (§6) documents `CONFIG_ARM64_16K_PAGES` as the
canonical arm64 switch. The pre-A10 iPad generations also run 16K in Hoolock
work, but that is outside our scope.

## 6. Android 15/16 16 KB support — what is checked, exactly

All citations fetched 2026-11-05.

**Kernel**: `CONFIG_ARM64_16K_PAGES=y` is the documented switch
(source.android.com "16 KB page size", `docs/core/architecture/16kb-page-size/16kb`),
for Kleaf builds `--page_size=16k`. The AOSP "requires a 16K kernel for
arm64; 16K userspace" design applies from Android 15 onward: **Android 15+
supports building with 16 KB ELF alignment that works with 4 KB and 16 KB
kernels starting with `android14-6.1`** — i.e. a 16K-ELF-aligned system
image is the portable sweet spot for our 16K Orchard kernel.

**Userspace build** (same source page, VERIFIED): `PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO
:= true`, `PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384` guarantee 16 KB ELF
alignment of platform natives; non-AOSP libs need `-Wl,-z,max-page-size=16384`.
Page-agnostic targets exist: `aosp_cf_arm64_phone_pgagnostic` (Cuttlefish
built from `android-latest-release`, `lunch aosp_cf_arm64_phone_pgagnostic-aosp_current-userdebug`,
getconf PAGE_SIZE = 16384 — the doc's *getting-started-cf-arm64-pgagnostic*).
**Android 16** adds `PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := true` to catch
non-aligned prebuilts at build time, and `atest elf_alignment_test` for
on-device verification. Vts16KPageSizeTest + `ro.product.page_size` exists as
the device-side verifier (source.android.com system-properties page).

**App compat**: Android 16's "16 KB page size compatibility mode" lets the
package manager run apps whose ELFs/AAP stack are still 4K (source:
`developer.android.com/about/versions/16/summary`, "Core functionality |
16 KB page size compatibility mode"; mechanism documented at
`developer.android.com/guide/practices/page-sizes`: back-compat mode
activates when a device runs a 16 KB kernel and apps ship `.so` with 4K LOAD
alignment and a 4K-aligned zip section when applicable). Play-side deadline:
all apps targeting API 35+ must support 16K from Feb 1 2027 (same page),
which keeps Track-B GSI longterm-viable.

**GSIs (facts + risks, no invention):**

- Google publishes Android 16 GSIs (ARM64 A/B "arm64-exp" both vanilla and
  GMS; builds BP2A.250605.031.A3 June 3 2025 and the QPR3-beta track
  CP11.251209.009.A1 of Feb 2026 documented at
  `developer.android.com/about/versions/16/gsi-release-notes[-qpr]`). These
  are **evaluation-only, non-CTS-approved** binaries (same pages).
- Whether the currently published official ARM64 GSI binaries are built
  16K-aligned is **not stated in their release notes** → treat as
  ASSUMED-both-ways; our Track-B decision requires either (a) building the
  GSI ourselves from AOSP with `PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384` +
  `PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO := true` (the direction the mission
  prefers), or (b) buying the correctness empirically at M2 with a check
  script (`getconf PAGE_SIZE`, ELF max-page-size sweep) before claiming any
  "16K-capable".
- LineageOS as a GSI: **LineageOS itself does not publish official *GSI*
  images**; the widely used GSI builds are community projects built from
  Lineage sources with Treble overlays. Source: MisterZtr's lineage-22.2 GSI
  README (verified page: builds `lineage_arm64_bvN*` targets, erofs or
  ext4) and the TrebleDroid GSI list. "Official LineageOS GSI" in the
  mission is therefore a misnomer: Track A = community GSI builds of
  Lineage sources.
- **Decision (2026-11-05, project owner):** Track B uses **Google's
  published AOSP GSI binaries** (`aosp_arm64-exp-*`, vanilla) as the
  starting userland — no custom build until the published binaries are
  proven insufficient. Community Lineage GSIs are deferred. The Orchard
  kernel stays as-is (`apple-16k`); the only kernel delta for Android is the
  binder/bindinery fragment in `kernelspace/android-binder.cfg`
  (docs/android-kernel-delta.md). If the published GSI turns out 4K-built,
  the fallback order is: (1) page-compat behaviour of Android 16 for the
  system image as it exists, (2) a one-off AOSP build with
  `PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384` + `PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO
  := true`. Honest for now: the boot attempt itself is the measurement
  (M2 ELF sweep + `getconf PAGE_SIZE` on device).

## 7. Project Sandcastle prior art, what to reuse

Read 2026-11-05, `corellium/projectsandcastle` `master` README (VERIFIED):

- Their utilities: `loader/` (pongoOS payload hosting), `syscfg/` config
  extraction tool, `hx-touchd` touch daemon (iPhone 6s-class), `hcdpack` BT
  firmware heuristics extractor; Linux fork `corellium/linux-sandcastle`,
  buildroot ramdisk `corellium/sandcastle-buildroot`.
- **Their 16K userspace law is exactly the law we implement**: rebuild
  binaries with `-z max-page-size=0x4000 (-Wl,-z,common-page-size=0x4000)`,
  `readelf -l` to confirm RELRO/LOAD alignment on 16K boundaries, and hunt
  hardcoded `4096/0x1000/PAGE_SIZE=12` — Chromium called out as an offender.
  Cite this in docs/SANDCASTLE.md as the convergence point of two
  independent projects.
- Architecture difference to record: Sandcastle ran **Android on their
  Linux kernel as a chroot-like process tree** (their README's install
  section shows Android apps served from a Linux userland) — proof Android
  userland + Apple A10 works; our architecture is a true Android init
  userland on m1n1/Orchard's nvme/DRM/Z2 stack.
- License posture: per-repo (kernel fork is GPL-2.0 via Linux; userspace
  loader/hcdpack under their per-fat LICENSE). We only credit-and-consult
  until M1, when any copied source line has its SPDX recorded in NOTICE and
  docs/SANDCASTLE.md.

## 8. iPad 7 vs iPad 6 fork-relevant diffs (for M0 CI/profile build)

From the omarchy-a fork, device profile build uses `orchard.local.toml`
`device = "j171"` (README pattern). ===== …J171 needs from our side:

- Boot assets and firmware recipe: provided by orchard/`devices/j171`,
  including Broadcom `brcmfmac4355c1-pcie.apple,rudderb.bin` etc., DFP
  SmartIO, HCDs by `bluetool`, and Z2 touch firmware via `z2fw-from-mtfw`
  (`J171_multitouch…im4p` → `dfrmtfw-j172-k1f19-6.bin`) — CONFIRMED machine
  recipe in `devices/j171/firmware.json` (VERIFIED). iPad 6 differs mainly in
  per-board DTS files and Wi-Fi firmware naming; the recipe style is shared.
- The CI will need the release skeleton to accept a different device id in
  `orchard.toml`/`orchard.local.toml`; final wiring in M0 build task.

## 9. Security, legal, and installer defaults (deltas from Omarchy A)

- No auto-login/`tablet` user concept is carried into Android; Android runs
  as normal (first user on boot, app sandboxing, lock screen immediately).
- ADB over USB is off by default; the dev flag (`orchard logcat --enable-adb`)
  flips it via vendor-layer persistent prop, requires confirming in UI on the
  iPad. (Design note; verify limited to M3 logcat milestone.)
- Apple/Broadcom/Z2 firmware only ever extracted on the user's machine from
  their own .ipsw via the verified Installer recipe (paths recorded in
  `devices/j171/firmware.json`), never redistributed — same stance as
  omarchy-a.
- No iCloud/activation bypass, no iCloud-locked devices; checkm8 covers
  BootROM exploitation of devices the user owns (per mission legality note).
- Typed-confirmation data-loss warning is already omarchy-a's install
  pattern (README "Back up your iPad" + typed confirm) — reuse verbatim.

## 10. Open questions to answer with tests (M0 → M2)

| # | Question | Test / current state |
|---|---|---|
| 1 | Does the j171 DTS actually build (DTB name `t8010-j171`)? | build the kernel series and list `arch/arm64/boot/dts/apple/t8010-j171.dtb` — M0 CI after profile wiring |
| 2 | Which touch driver runtime form ships for j171 (in-tree apple_z2 vs out-of-tree `j71b_z2.ko`)? | inspect `modules`-build outputs at M1 |
| 3 | Are published Google GSIs 16K-aligned? | run the ELF `max-page-size` sweep over `system.img` of candidate builds at M2 before choosing | 
| 4 | Mesa "G9P" public source? | locate fork, record license in NOTICE/SANDCASTLE — before any userspace packaging |
| 5 | Does SurfaceFlinger like the `adbe` DRM KMS path (16K ELF build)? | M3 boot with `getconf PAGE_SIZE` + logcat log |
| 6 | Charging > 500 mA state on J171 | follow devices/j171/README test plan from orchard (user-owned hardware required) |
| 7 | Android first-stage init on a non-dynamic partition with our initrd model | M2 boot smoke (initramfs shell → `exec init=/init`) |

## 11. Assumptions inventory (must be retired by M2)

1. **BLE/Bluetooth on iPad 7** — firmwares exist in the recipe; in-tree hci
   support exists (claims above); runtime ordering unknown. Marked **ASSUMED,
   none working on Android yet**; M6.
2. **Google GSI 16K alignment** — §6 (4).
3. **`aosp_cf_arm64_phone_pgagnostic` target names still current in
   `android-latest-release`** — check via a CI build listing on branch
   `aosp-main-throttled` before pinning the Track-B build recipe.
4. **`t8010-j171.dtb` build target presence in the series output** — build
   (table row 1).
5. **iPad 7 set-relevant ADT fill-ins** apply the same aliases
   (wifi0/bluetooth0/touchscreen0) as iPad 6 — inferred from the DTS patch +
   boot contract; verify ADT dump on hardware when available.

Where anything in this doc conflicts with a to-be-run test, the test wins.
