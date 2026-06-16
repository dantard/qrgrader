import sys
import argparse

from qrgrader import qrworkspace, qrgui

# your sub-scripts

args_input = sys.argv
help_requested = '-h' in args_input or '--help' in args_input
if help_requested:
    sys.argv = [arg for arg in args_input if arg not in ('-h', '--help')]

parser = argparse.ArgumentParser(description='QR tools')
subparsers = parser.add_subparsers(dest='command', required=True)

subparsers.add_parser('workspace', help='Sync workspace')
subparsers.add_parser('gui', help='Build workspace')


# parse only the subcommand, leave the rest untouched
args, remaining = parser.parse_known_args()

if help_requested:
    remaining += ['--help']

if args.command == 'workspace':
    sys.argv = ['qrworkspace'] + remaining  # patch argv for the sub-script
    qrworkspace.main()

elif args.command == 'gui':
    sys.argv = ['qrgui'] + remaining
    if __name__ == '__main__':
        qrgui.main()
