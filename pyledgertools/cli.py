#! /usr/bin/env python3
"""Command line interface for ledgertools package."""

from argparse import ArgumentParser
from configparser import ConfigParser
import os
from os.path import expanduser
import re
import sys
from subprocess import Popen, PIPE
from yapsy.PluginManager import PluginManager
import yaml

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
    parser.add_argument(
        '-s', '--dtstart',
        dest='dtstart',
        default='20170301',
        help='Date to start pulling transactions from.'
    )
    parser.add_argument(
        '-e', '--dtend',
        dest='dtend',
        default='20170320',
        help='Date to start pulling transactions from.'
    )
    args = parser.parse_args()

    return dict((k, v) for k, v in vars(args).items() if v)


def get_plugin(manager, name):
    """Find a plugin by name."""
    for plugin in manager.getAllPlugins():
        if plugin.name == name:
            return plugin.plugin_object

    return None


def interactive():
    """Run the command line interface."""

    default_config = os.path.join(
        expanduser("~"), '.config', 'ledgertools', 'ledgertools.yaml'
    )

    # Load Plugins
    manager = PluginManager()
    manager.setPluginPlaces([os.path.join(DIR_PATH, 'plugins')])
    manager.collectPlugins()

    # Load classification plugins
    rule = get_plugin(manager, 'Rule Based Classifier')
    bayes = get_plugin(manager, 'Naive Bayes Classifier')

    # Load command line options.
    cli_options = get_args()

    c_path = cli_options.get('config', default_config)

    with open(c_path, 'r') as f:
        config = yaml.load(f)

    balances = []
    transactions = []

    # -------------------------------------------------------------------------
    # Start processing
    # -------------------------------------------------------------------------
    global_conf = config.get('global', {})

    accounts = args.account.split(',')

    for account in accounts:
        base_conf = global_conf
        conf = config.get(account, None)
        parent_conf = config.get(conf.get('parent', 'NaN'), {})

        base_conf.update(parent_conf)
        base_conf.update(conf)
        base_conf.update(cli_options)
        conf = base_conf

        # Get downloader and parser plugins fromthe config.
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
        process = Popen(['ledger', 'print'], stdout=PIPE)
        journal, err = process.communicate()
        interactive_classifier = bayes.setup(journal_file=journal)

    try:
        rules = rule.build_rules(conf['rules_file'])
    except KeyError:
        rules = None

    # Make list of existing UUID's
    regex = 'UUID:\s+([a-z0-9]+)'
    process = Popen(['ledger', '--format', '"%N\n"', 'reg'], stdout=PIPE)
    ledger_data, err = process.communicate()
    uuid_results = re.findall(regex, str(ledger_data))

    for transaction in transactions:
        if transaction.uuid not in uuid_results:
            match = None
            result = None
            selected_account = None

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

            if (conf['rules_file'] is None or found_rule == {}) and skip is False:
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
                selected_account = input(': ')
                print('')
            elif isinstance(result, list):
                for i, acc in enumerate(result[:5]):
                    print('[{}] {}'.format(i, acc))
                print('[e] Enter New Account')
                print('[s] Skip Transaction')

                user_in = input('Enter Selection: ').strip()

                try:
                    selection = int(user_in)
                    selected_account = result[selection][0]

                except ValueError:
                    if user_in == 'e':
                        selected_account = input('Enter account name: ').strip()

            if selected_account:
                print('Using ', selected_account)
                print('')

                interactive_classifier.update(text, selected_account)

                transaction.add(selected_account, amount * -1, currency)

                print('---------------------')
                print(transaction.to_string())
                with open(conf['ledger_file'], 'a') as outfile:
                    print(transaction.to_string(), '\n', file=outfile)

                selected_account = None

            print('')
            print('=' * 80)


if __name__ == "__main__":
    interactive()
