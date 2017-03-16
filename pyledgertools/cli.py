#! /usr/bin/env python3

from argparse import ArgumentParser
from yaml import load

from pyledgertools.ofx2ledger import build_journal
from os.path import expanduser


def get_args():
    """Build CLI arguments list."""

    parser = ArgumentParser()

    parser.add_argument(
        "-i", "--input-ofx",
        dest="ofx_file",
        default=None,
        help=".OFX file to parse"
    )
    parser.add_argument(
        "-l", "--ledger-file",
        dest="ledger_file",
        default=None,
        help="Ledger file to check transactions against."
    )
    parser.add_argument(
        "-c", "--config",
        dest="config",
        default=None,
        help="config file for account names/numbers etc."
    )
    parser.add_argument(
        "-r", "--rules",
        dest="rule_file",
        default='rules.txt',
        help="File or directory containing matching rules."
    )

    args = parser.parse_args()

    return args


def main():
    home = expanduser("~")

    args = get_args()

    if args.config:
        c_path = args.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(home,'.conf','ledgertools', 'ofx.conf')

    config = load(open(c_path, 'r'))

    build_journal(args.ofx_file, config['accounts'])


if __name__ == "__main__":
    main()

