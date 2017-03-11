#! /usr/bin/env python3

from argparse import ArgumentParser
from yaml import load

from pyledgertools.ofx2leddger import build_journal

parser = ArgumentParser()

parser.add_option(
    "-i", "--input-ofx",
    dest="ofx_file",
    default=None,
    help=".OFX file to parse"
)
parser.add_option(
    "-l", "--ledger-file",
    dest="ledger_file",
    default=None,
    help="Ledger file to check transactions against."
)
parser.add_option(
    "-c", "--config",
    dest="config",
    default=None,
    help="config file for account names/numbers etc."
)
parser.add_option(
    "-r", "--rules",
    dest="rule_file",
    default='rules.txt',
    help="File or directory containing matching rules."
)

options = parser.parse_args()

if __name__ == "__main__":
    if options.config:
        c_path = options.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(ROOT, 'ofx.conf')

    config = load(open(c_path, 'r'))

    build_journal(options.ofx_file, config['accounts'])