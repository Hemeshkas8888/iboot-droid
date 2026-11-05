iBoot Droid vendor SELinux policy (placeholder, honest state)

Nothing is precompiled here yet. The GSI ships the system policy; our vendor
stub policy gets added only when a boot log shows a denial that blocks boot
completion (M3), and then as narrow exceptions — not a blanket "allow all",
which would weaken the system policy.
