#! /usr/bin/env python3
"""Command line interface for ledgertools package."""

from argparse import ArgumentParser
from configparser import ConfigParser
import os
from os.path import expanduser
import re
import sys
import tempfile
from subprocess import Popen, PIPE, call
from yapsy.PluginManager import PluginManager
import yaml

from pyledgertools.strings import UI, Info, Prompts
from pyledgertools.functions import amount_group

DIR_PATH = os.path.dirname(os.path.realpath(__file__))


def get_args():
    """Build CLI arguments list."""

    parser = ArgumentParser()

    parser.add_argument(
        '-i', '--input-file',
        dest='input_file',
        default=None,
        help='.OFX file to parse'
    )
    parser.add_argument(
        '-l', '--ledger-file',
        dest='journal_file',
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


def read_ledger(journal=None):
    """Read a ledger journal and return formatted transactions."""

    if journal is None:
        cmd = ['ledger', 'print', '--limit', 'payee!~/Opening Balance/']
    else:
        cmd = ['ledger', '-f', journal, 'print', '--limit', 'payee!~/Opening Balance/']

    process = Popen(cmd, stdout=PIPE)
    journal, err = process.communicate()

    return journal


def list_uuids(journal=None):
    """Pull list of UUID's from ledger journal."""

    if journal is None:
        cmd = ['ledger', '--format', '"%N\n"', 'reg']
    else:
        cmd = ['ledger', '-f', journal, '--format', '"%N\n"', 'reg']

    # Make list of existing UUID's
    regex = 'UUID:\s+([a-z0-9]+)'
    process = Popen(cmd, stdout=PIPE)
    ledger_data, err = process.communicate()
    return re.findall(regex, str(ledger_data))


def vim_input(text='', offset=None):
    """Use editor for input."""
    editor = os.environ.get('EDITOR', 'vim')

    proc = Popen(['accounts'], stdout=PIPE)
    ledger_accounts = proc.stdout.read()

    text += '    \n;;* Account Completion *;;\n2017-01-01 Completion Accounts\n'
    text += ledger_accounts.decode('utf-8')

    with tempfile.NamedTemporaryFile(suffix='.ledger') as tf:
        tf.write(text.encode())
        tf.flush()
        if offset:
            call([editor, '+' + str(offset), tf.name])
        else:
            call([editor, tf.name])

        tf.seek(0)
        for line in tf.readlines():
            if not line.startswith(b'#') and line.strip() != '':
                return line.strip().decode('utf-8')


def automatic():
    """Run the command line interface without user input."""

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

    # -------------------------------------------------------------------------
    # Start processing
    # -------------------------------------------------------------------------
    global_conf = config.get('global', {})

    accounts = cli_options['account'].split(',')

    learning_global = read_ledger()

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

        file_path = conf.get('input_file', None)
        try:
            if not file_path:
                file_path = getter.download(conf)
        except:
            continue

        balances, transactions = parser.build_journal(file_path, conf)

        transactions.sort(key=lambda x: x.date)

        learning_file = conf.get('journal_file', None)
        if not learning_file:
            learning_file = learning_global

        interactive_classifier = bayes.setup(journal_file=learning_file)
        rules = rule.build_rules(conf.get('rules_file', None))
        uuids = list_uuids()

        for transaction in transactions:
            if transaction.uuid not in uuids:
                result = None
                selected_account = None

                text = transaction.payee
                amount = transaction.postings[0].amount
                currency = transaction.postings[0].currency

                found_rule = rule.find_matching_rule(rules, transaction)

                # Check for keys in rule
                skip = found_rule.get('ignore', False)
                process = found_rule.get('process', None)
                allocations = found_rule.get('allocations', None)

                if all(x in [False, None] for x in [skip, process, allocations]):
                    result = interactive_classifier.classify(
                        text + ' ' + amount_group(amount),
                        method='bayes'
                    )
                    cleaned = [x for x in result if round(x[1], 10) > 0]
                    if len(cleaned) > 0:
                        result = cleaned

                print('\n', UI.double_line)
                print(transaction.to_string(), '\n')

                if skip is True:
                    print(Info.skip_deposit_side)
                    pass
                elif result is None:
                    selected_account = conf.get('to', 'Expenses:Unkown')
                    print('')
                elif isinstance(result, list):
                    selected_account = result[0][0]

                if selected_account:
                    interactive_classifier.update(
                        text + ' ' + amount_group(amount),
                        selected_account
                    )
                    transaction.add(selected_account, amount * -1, currency)

                    print('\n', UI.single_line)
                    print(transaction.to_string())
                    with open(conf['ledger_file'], 'a') as outfile:
                        print(transaction.to_string() + '\n', file=outfile)

                    selected_account = None

                print('\n', UI.double_line)

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

    # -------------------------------------------------------------------------
    # Start processing
    # -------------------------------------------------------------------------
    global_conf = config.get('global', {})

    accounts = cli_options['account'].split(',')

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

        file_path = conf.get('input_file', None)
        try:
            if not file_path:
                file_path = getter.download(conf)
        except:
            continue

        balances, transactions = parser.build_journal(file_path, conf)

        transactions.sort(key=lambda x: x.date)

        learning_file = conf.get('journal_file', read_ledger())
        interactive_classifier = bayes.setup(journal_file=learning_file)
        rules = rule.build_rules(conf.get('rules_file', None))
        uuids = list_uuids()

        for transaction in transactions:
            if transaction.uuid not in uuids:
                result = None
                selected_account = None

                text = transaction.payee
                amount = transaction.postings[0].amount
                currency = transaction.postings[0].currency

                found_rule = rule.find_matching_rule(rules, transaction)

                # Check for keys in rule
                skip = found_rule.get('ignore', False)
                process = found_rule.get('process', None)
                allocations = found_rule.get('allocations', None)

                if all(x in [False, None] for x in [skip, process, allocations]):
                    result = interactive_classifier.classify(
                        text + ' ' + amount_group(amount),
                        method='bayes'
                    )
                    cleaned = [x for x in result if round(x[1], 10) > 0]
                    if len(cleaned) > 0:
                        result = cleaned

                print('\n', UI.double_line)
                print(transaction.to_string(), '\n')

                if skip is True:
                    print(Info.skip_deposit_side)
                    pass
                elif result is None:
                    print(Prompts.needs_manual_entry)
                    selected_account = input(': ')
                    print('')
                elif isinstance(result, list) and len(result) == 1:
                    selected_account = result[0][0]
                elif isinstance(result, list):
                    for i, acc in enumerate(result[:5]):
                        print(Prompts.bayes_result.format(i, acc))
                    print(Prompts.opt_enter)
                    print(Prompts.opt_skip)

                    user_in = input(Prompts.enter_select).strip()

                    try:
                        selection = int(user_in)
                        selected_account = result[selection][0]

                    except ValueError:
                        if user_in == Prompts.opt_e_key:
                            selected_account = vim_input(
                                Info.vim_helper.format(text, currency, amount),
                                offset=4
                            )
                            selected_account = selected_account.strip()

                if selected_account:
                    interactive_classifier.update(
                        text + ' ' + amount_group(amount),
                        selected_account
                    )
                    transaction.add(selected_account, amount * -1, currency)

                    print('\n', UI.single_line)
                    print(transaction.to_string())
                    with open(conf['ledger_file'], 'a') as outfile:
                        print(transaction.to_string() + '\n', file=outfile)

                    selected_account = None

                print('\n', UI.double_line)


if __name__ == "__main__":
    interactive()
