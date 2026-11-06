# Device logs

Verified on-device evidence per milestone. Device: iPad 7th gen Wi-Fi (iPad7,11 /
`apple,j171` / `apple,t8010`), palera1n v2.4 over checkm8, orchard checkout

## M1 — kernel + recovery RAM boot (VERIFIED 2026-11-06)

`../orchard/bin/orchard run`, release `dev-20261106-054242`:

- palera1n 2.4 conducts checkm8; Pongo loads patched m1n1; m1n1 splash on screen.
- launcher observation: `"recovery_observed": true`; USB device shows
  `mode: linux`, `product: Orchard Recovery`, `profile: j171`
  (`/dev/cu.usbmodem1103`).
- serial probe (115200 baud) on the device itself:

```
uname -a
Linux (none) 7.3.0-rc1-orchard-apple-16k #1 SMP PREEMPT 2026-10-22T00:00:00Z aarch64 GNU/Linux
cat /proc/device-tree/compatible
apple,j171  apple,t8010  apple,arm-platform
```

- dmesg baseline: Apple Fusion PMU; pcie-apple-h9p host bridge up
  (106b:1007/1008); ANS2 NVMe endpoint 106b:2002 on root port 0; Broadcom
  14e4:43dc (BCM4355 Wi-Fi) endpoint on root port 3; gadgetfs; squashfs;
  initrd freed normally.
- RAM boot only; no storage partitions were written (`orchard run`: nothing installed).
