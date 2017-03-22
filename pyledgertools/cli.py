#! /usr/bin/env python3

from argparse import ArgumentParser
from configparser import ConfigParser
import os
from os.path import expanduser
import sys
from yapsy.PluginManager import PluginManager

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


def get_args():
    """Build CLI arguments list."""

    parser = ArgumentParser()

    parser.add_argument(
        '-i', '--input-ofx',
        dest='ofx_file',
        default=None,
        help='.OFX file to parse'
    )
    parser.add_argument(
        '-l', '--ledger-file',
        dest='ledger_file',
        default=None,
        help='Ledger file to check transactions against.'
    )
    parser.add_argument(
        '-c', '--config',
        dest='config',
        default=None,
        help='config file for account names/numbers etc.'
    )
    parser.add_argument(
        '-r', '--rules',
        dest='rule_file',
        default=None,
        help='File or directory containing matching rules.'
    )
    parser.add_argument(
        '-a', '--account',
        dest='account',
        default=None,
        help='Config section to use for import.'
    )
    args = parser.parse_args()

    return args


def get_plugin(manager, name):
    """Find a plugin by name."""
    for plugin in manager.getAllPlugins():
        if plugin.name == name:
            return plugin.plugin_object

    return None


def interactive():
    """Run the command line interface."""
    # Load Plugins
    manager = PluginManager()
    manager.setPluginPlaces([
        os.path.join(DIR_PATH, 'plugins')
    ])

    manager.collectPlugins()

    # Load classification plugins
    rule = get_plugin(manager, 'Rule Based Classifier')
    bayes = get_plugin(manager, 'Naive Bayes Classifier')

    args = get_args()

    # Load Config file
    if args.config:
        c_path = args.config
    else:
        c_path = os.path.join(
            expanduser("~"), '.config', 'ofxtools', 'ofxget.conf'
        )

    config = ConfigParser()
    config.read(c_path)

    balances = []
    transactions = []

    # -------------------------------------------------------------------------
    # Test suntrust
    # -------------------------------------------------------------------------
    conf = dict(config.items(args.account))
    try:
        base_conf = dict(config.items(conf['global']))
    except KeyError:
        base_conf = {}

    try:
        parent_conf = dict(config.items(conf['parent']))
    except KeyError:
        parent_conf = {}

    base_conf.update(parent_conf)
    base_conf.update(conf)
    conf = base_conf

    getter = get_plugin(manager, conf['downloader'])
    parser = get_plugin(manager, conf['parser'])

    if args.ofx_file is None:
        file_path = getter.download(conf)
    else:
        file_path = args.ofx_file

    bal, trans = parser.build_journal(file_path, conf)

    balances = balances + bal
    transactions = transactions + trans

    transactions.sort(key=lambda x: x.date)

    if args.ledger_file is not None:
        interactive_classifier = bayes.setup(journal_file=args.ledger_file)
    else:
        interactive_classifier = bayes.setup()

    if args.rule_file is not None:
        rules = rule.build_rules(args.rule_file)
    else:
        rules = None

    for transaction in transactions:
        match = None
        result = None
        text = transaction.payee
        amount = transaction.postings[0].amount
        currency = transaction.postings[0].currency

        for entry in rules.keys():
            match = rule.walk_rules(rules[entry]['conditions'], transaction)
            if match:
                found_rule = rules[entry]
                break
                sys.exit()
            else:
                found_rule = {}

        try:
            skip = found_rule['ignore']
        except KeyError:
            skip = False

        if (args.rule_file is None or found_rule == {}) and skip is False:
            result = interactive_classifier.classify(text, method='bayes')

        print('')
        print('=' * 80)
        print(transaction.to_string())
        print('')
        if skip is True:
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

            transaction.add(account, amount * -1, currency)

            print('---------------------')
            print(transaction.to_string())
            with open(conf['ledger_file'], 'a') as outfile:
                print(transaction.to_string(), '\n', file=outfile)

            account = None

        print('')
        print('=' * 80)


if __name__ == "__main__":
    interactive()
