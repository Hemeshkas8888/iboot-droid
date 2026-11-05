"""The Android vendor layer: determinism, contents, and honest stubs."""
from pathlib import Path
import hashlib
import tarfile
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


def load(module_name, path):
    path = Path(path)
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        namespace = {'__name__': module_name, '__file__': str(path)}
        exec(compile(path.read_text(), str(path), 'exec'), namespace)
        return type('Module', (), namespace)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def code_lines(path):
    return (Path(path).read_text().splitlines()
            and [line for line in Path(path).read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')])


class VendorLayerArtifact(unittest.TestCase):
    def test_the_same_input_builds_the_same_bytes(self):
        build = load('ibootdroid_build_vendor', PROJECT / 'android/build-vendor')
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / 'a.tar.gz'
            second = Path(tmp) / 'b.tar.gz'
            with first.open('wb') as stream:
                build.produce(stream)
            with second.open('wb') as stream:
                build.produce(stream)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest())

    def test_coverage_of_the_layer_files(self):
        build = load('ibootdroid_build_vendor', PROJECT / 'android/build-vendor')
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / 'vendor-layer.tar.gz'
            with artifact.open('wb') as stream:
                build.produce(stream)
            names = {member.name for member in tarfile.open(artifact)}
            for name in ('etc/fstab.ibootdroid', 'etc/init/init.ibootdroid.rc',
                         'etc/init/ueventd.ibootdroid.rc', 'etc/vintf/manifest.xml'):
                with self.subTest(member=name):
                    self.assertIn(name, names)


class VendorLayerHonesty(unittest.TestCase):
    def setUp(self):
        fstab_lines = code_lines(PROJECT / 'android/vendor/etc/fstab.ibootdroid')
        tokens = ' '.join(fstab_lines).split()
        self.partition_markers = sorted(set(t.split('@', 1)[1].split(',', 1)[0]
                                            for t in tokens if t.startswith('@')))

    def test_fstab_names_its_four_installer_substituted_partitions(self):
        self.assertEqual(self.partition_markers[:1], ['BOOTPARTUUID'])
        self.assertEqual(
            sorted(self.partition_markers),
            ['BOOTPARTUUID', 'DATAPARTUUID', 'SYSTEMPARTUUID', 'VENDORPARTUUID'])

    def test_no_hal_services_claimed_without_a_log(self):
        for rc in sorted((PROJECT / 'android/vendor/etc/init').glob('*.rc')):
            with self.subTest(rc=rc.name):
                text = '\n'.join(code_lines(rc))
                self.assertNotIn('service ', text,
                                 'no stub service may pretend a binary exists; add it with its log')


if __name__ == '__main__':
    unittest.main()
