#! /usr/bin/env python3

from argparse import ArgumentParser
from yaml import load

from pyledgertools.ofx2ledger import build_journal

def main():

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

    options = parser.parse_args()

    if options.config:
        c_path = options.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(ROOT, 'ofx.conf')

    config = load(open(c_path, 'r'))

    build_journal(options.ofx_file, config['accounts'])


if __name__ == "__main__":
    main()

