#! /usr/bin/env python3

from argparse import ArgumentParser
import os
from os.path import expanduser
from yaml import load
from yapsy.PluginManager import PluginManager
from yapsy.IPlugin import IPlugin

from pyledgertools.ofx2ledger import build_journal
from pyledgertools.plugin import IDownload, IClassify, IModify

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


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
    """Run the command line interface."""
    # Build the manager.
    plugin_manager = PluginManager()

    plugin_manager.setCategoriesFilter({
        'classify': IClassify,
        'download': IDownload,
        'modify': IModify,
    })

    # Tell it the default place(s) where to find plugins.
    plugin_manager.setPluginPlaces([
        os.path.join(DIR_PATH, 'plugins')
    ])

    plugin_manager.collectPlugins()

    print('All', [x.name for x in plugin_manager.getAllPlugins()])
    print('Download', [x.name for x in plugin_manager.getPluginsOfCategory('download')])
    print('Classify', [x.name for x in plugin_manager.getPluginsOfCategory('classify')])
    print('Modify', [x.name for x in plugin_manager.getPluginsOfCategory('modify')])

    from configparser import ConfigParser

    config = ConfigParser()

    home = expanduser("~")

    args = get_args()

    if args.config:
        c_path = args.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(home,'.config','ofxtools', 'ofxget.conf')

    config.read(c_path)

    return build_journal(args.ofx_file, config)


def interactive():
    import sys
    from pyledgertools.classifier import Classifier
    from pyledgertools.rule_parser import walk_rules, build_rules

    args = get_args()
    bal, trans = main()

    trans.sort(key=lambda x: x.date)

    if args.ledger_file is not None:
        interactive_classifier = Classifier(journal_file=args.ledger_file)
    else:
        interactive_classifier = Classifier()

    for posting in trans:
        match = None
        result = None
        text = posting.payee
        amount = posting.allocations[0].amount
        currency = posting.allocations[0].currency

        if args.rule_file is not None:
            rules = build_rules(args.rule_file)

        for rule in rules.keys():
            match = walk_rules(rules[rule]['conditions'], posting)
            if match:
                found_rule = rules[rule]
                break
                sys.exit()
            else:
                found_rule = {}

        try:
            skip = found_rule['ignore']
        except KeyError:
            skip = False

        if (args.rule_file is None or found_rule == {}) and skip == False:
            result = interactive_classifier.classify(text, method='bayes')

        print('')
        print('=' * 80)
        print(posting.to_string())
        print('')
        if skip == True:
            print('Skip transfer Deposit')
            pass
        elif result is None:
            print('No matches found, enter an account name:')
            account = input(': ')
            print('')
        elif isinstance(result, list):
            for i, acc in enumerate(result[:5]):
                print('[{}] {}'.format(i, acc))
            print('[e] Enter New Account')
            print('[s] Skip Transaction')

            user_in = input('Enter Selection: ').strip()

            try:
                selection = int(user_in)
                account = result[selection][0]

            except ValueError:
                if user_in == 'e':
                    account = input('Enter account name: ').strip()

                else:
                    account = None

        if account:
            print('Using ', account)
            print('')


            interactive_classifier.update(text, account)

            posting.add(account, amount * -1, currency)

            print('---------------------')
            print(posting.to_string())
            with open('tmp.ledger', 'a') as outfile:
                print(posting.to_string(), '\n', file=outfile)

        print('')
        print('=' * 80)


if __name__ == "__main__":
    main()

