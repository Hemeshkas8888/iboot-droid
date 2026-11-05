#!/usr/bin/env python3
"""Apply or check the iBoot Droid Android kernel fragment over a `.config`.

The kernel stays the orchard `apple-16k` build; this only flips the options
Android needs (see docs/android-kernel-delta.md). Options never delete:
the merge is additive over the platform config.

  kernelspace/apply_fragment.py --base CONFIG --output NEW  (merge, additive)
  kernelspace/apply_fragment.py --base CONFIG --check      (validate; exit 1 on any miss)
"""
import argparse
import sys
from pathlib import Path

FRAGMENT = Path(__file__).resolve().parent / 'android-binder.cfg'


def parse_config(text):
    """{symbol: value-string} of active assignments and '# CONFIG_X is not set'."""
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('CONFIG_') and '=' in stripped:
            key, value = stripped.split('=', 1)
            values[key] = value
        elif stripped.startswith('# CONFIG_') and stripped.endswith('is not set'):
            key = stripped[2:-len(' is not set')]
            values[key] = 'n'
    return values


def parse_fragment(text):
    """{symbol: value-string} from android-binder.cfg."""
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if not line.startswith('CONFIG_') or '=' not in line:
            sys.exit(f'fragment line is not an assignment: {line!r}')
        key, value = line.split('=', 1)
        values[key] = value
    return values


def merge(base, translations):
    """Replace/add assignments for each TRANSLATIONS symbol; never remove."""
    out = []
    consumed = set()
    for line in base.splitlines():
        stripped = line.strip()
        key = None
        if stripped.startswith('CONFIG_') and '=' in stripped:
            key = stripped.split('=', 1)[0]
        elif stripped.startswith('# CONFIG_') and stripped.endswith('is not set'):
            key = stripped[2:-len(' is not set')]
        if key in translations:
            consumed.add(key)
            out.append(f'{key}={translations[key]}')
        else:
            out.append(line)
    missing = [f'{k}={translations[k]}' for k in translations if k not in consumed]
    if missing:
        out.extend(missing)
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, help='the platform .config to build on')
    parser.add_argument('--output', type=Path, help='merged config output path')
    parser.add_argument('--check', action='store_true', help='verify BASE satisfies the fragment')
    args = parser.parse_args()
    if not args.base or not (args.check ^ bool(args.output)):
        parser.error('name --base with exactly one of --check or --output')

    wanted = parse_fragment(FRAGMENT.read_text())
    have = parse_config(args.base.read_text())
    errors = [f'{key}: fragment wants {value}, config has {have.get(key, "<absent>")}'
              for key, value in wanted.items() if have.get(key) != value]
    if args.check:
        for error in errors:
            print(error)
        raise SystemExit(1 if errors else 0)
    args.output.write_text(merge(args.base.read_text(), wanted))


if __name__ == '__main__':
    main()
