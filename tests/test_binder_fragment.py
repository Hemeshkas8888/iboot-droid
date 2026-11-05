"""The Android kernel fragment (binder + SELinux): shape, merge, check."""
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[1]
FRAGMENT = PROJECT / 'kernelspace/android-binder.cfg'
APPLIER = PROJECT / 'kernelspace/apply_fragment.py'


def load(module_name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = '\n'.join([
    '# synthetic platform config for the merge test',
    'CONFIG_ARM64_16K_PAGES=y',
    'CONFIG_ANDROID_BINDER_IPC=y',
    '# CONFIG_ANDROID_BINDERFS is not set',
    '# CONFIG_SECURITY_SELINUX is not set',
    '# CONFIG_CGROUP_FREEZER is not set',
    'CONFIG_EXT4_FS=y',
]) + '\n'

SATISFIED = '\n'.join([
    'CONFIG_ARM64_16K_PAGES=y',
    'CONFIG_ANDROID_BINDER_IPC=y',
    'CONFIG_ANDROID_BINDERFS=y',
    'CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder',
    'CONFIG_SECURITY_SELINUX=y',
    'CONFIG_SECURITY_SELINUX_DEVELOP=y',
    'CONFIG_CGROUP_FREEZER=y',
    'CONFIG_EXT4_FS=y',
]) + '\n'


class FragmentShape(unittest.TestCase):
    def test_fragment_is_a_single_flippable_assignment_per_option(self):
        applier = load('ibootdroid_apply_fragment', APPLIER)
        wanted = applier.parse_fragment(FRAGMENT.read_text())
        self.assertEqual(wanted, {
            'CONFIG_ANDROID_BINDER_IPC': 'y',
            'CONFIG_ANDROID_BINDERFS': 'y',
            'CONFIG_ANDROID_BINDER_DEVICES': 'binder,hwbinder,vndbinder',
            'CONFIG_SECURITY_SELINUX': 'y',
            'CONFIG_SECURITY_SELINUX_DEVELOP': 'y',
            'CONFIG_CGROUP_FREEZER': 'y',
        })


class FragmentMerge(unittest.TestCase):
    def test_merge_flips_and_adds_but_never_removes(self):
        applier = load('ibootdroid_apply_fragment', APPLIER)
        merged = applier.merge(BASE, applier.parse_fragment(FRAGMENT.read_text()))
        self.assertIn('CONFIG_ANDROID_BINDERFS=y\n', merged)
        self.assertIn('CONFIG_ANDROID_BINDER_IPC=y\n', merged)  # already on, unchanged
        self.assertIn('CONFIG_EXT4_FS=y\n', merged)             # unrelated, kept
        self.assertNotIn('is not set', merged)


class FragmentCheck(unittest.TestCase):
    def setUp(self):
        self.applier = load('ibootdroid_apply_fragment', APPLIER)

    def test_check_mode_validates_a_satisfying_config(self):
        wanted = self.applier.parse_fragment(FRAGMENT.read_text())
        have = self.applier.parse_config(SATISFIED)
        self.assertEqual([key for key, value in wanted.items() if have.get(key) != value], [])

    def test_check_mode_lists_every_miss(self):
        wanted = self.applier.parse_fragment(FRAGMENT.read_text())
        have = self.applier.parse_config(BASE)
        missing = sorted(key for key, value in wanted.items() if have.get(key) != value)
        self.assertEqual(missing, ['CONFIG_ANDROID_BINDERFS', 'CONFIG_ANDROID_BINDER_DEVICES',
                                   'CONFIG_CGROUP_FREEZER', 'CONFIG_SECURITY_SELINUX',
                                   'CONFIG_SECURITY_SELINUX_DEVELOP'])


class UpstreamKernel(unittest.TestCase):
    """When an orchard checkout is present, assert the baseline facts directly."""

    def test_the_apple_16k_config_has_binder_ipc_and_binderfs_room(self):
        checkout = Path(__import__('os').environ.get('ORCHARD_CHECKOUT') or
                        (PROJECT / '.upstream/orchard'))
        config = checkout / 'kernel/configs/apple-16k/config'
        if not config.exists():
            self.skipTest('no orchard checkout available')
        applier = load('ibootdroid_apply_fragment', APPLIER)
        have = applier.parse_config(config.read_text())
        self.assertEqual(have['CONFIG_ARM64_16K_PAGES'], 'y')
        self.assertEqual(have['CONFIG_ANDROID_BINDER_IPC'], 'y')


if __name__ == '__main__':
    unittest.main()
