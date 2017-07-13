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
import logging
import logging.config

from pyledgertools.strings import UI, Info, Prompts
from pyledgertools.functions import amount_group

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
HOME = expanduser("~")

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
    """Read a ledger journal and return fuuidsormatted transactions."""

    # Ignore opening balances and limit transactions to the
    # past 12 months.
    options = [
        '--limit', 'payee!~/Opening Balance/',
        '-p', 'from 12 months ago',
        '--raw'
    ]

    if journal is None:
        cmd = ['ledger', 'print'] + options
    else:
        cmd = ['ledger', '-f', journal, 'print'] + options

    process = Popen(cmd, stdout=PIPE)
    journal, err = process.communicate()

    return journal


def list_uuids(journal):
    """Pull list of UUID's from ledger journal."""

    # Make list of existing UUID's
    regex = 'UUID:\s+([a-z0-9]+)'
    return re.findall(regex, str(journal))


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
        HOME, '.config', 'ledgertools', 'ledgertools.yaml'
    )

    other_plugins = os.path.join(HOME, '.config', 'ledgertools', 'plugins')

    # Load Plugins
    manager = PluginManager()
    manager.setPluginPlaces([os.path.join(DIR_PATH, 'plugins'), other_plugins])
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

    logging.config.dictConfig(global_conf.get('logging', None))
    logger = logging.getLogger(__name__)
    logger.info('Process transactions started.')

    accounts = cli_options['account'].split(',')

    learning_file = read_ledger()

    uuids = list_uuids(learning_file)

    for account in accounts:
        logger.info('Processing ' + account)

        base_conf = global_conf
        account_config = config.get('accounts', None)

        conf = account_config.get(account, None)
        parent_conf = account_config.get(conf.get('parent', 'NaN'), {})

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
            logger.error('Error processing the account.')
            continue

        balances, transactions = parser.build_journal(file_path, conf)

        transactions.sort(key=lambda x: x.date)

        interactive_classifier = bayes.setup(journal_file=learning_file)
        rules = rule.build_rules(conf.get('rules_file', None))

        print_results = False
        str_out = ''

        # Build generator for filtered transactions
        filtered = (x for x in transactions if x.uuid not in uuids)
        for transaction in filtered:
            result = None
            postings = []

            text = transaction.payee
            amount = transaction.postings[0].amount
            currency = transaction.postings[0].currency

            found_rule = rule.find_matching_rule(rules, transaction)

            # Check for keys in rule
            skip = found_rule.get('ignore', False)
            process = found_rule.get('process', None)

            if skip is True:
                continue
            elif process:
                for plug in process.keys():
                    logger.info('Use plugin: {}'.format(plug))
                    logger.debug(process[plug])
                    plugin = get_plugin(manager, plug)
                    transaction = plugin.process(transaction, conf, process[plug])

            else: # Use classifier
                result = interactive_classifier.classify(
                    text + ' ' + amount_group(amount),
                    method='bayes'
                )
                result = [x for x in result if round(x[1], 10) > 0]
                if len(result) > 0:
                    posting = {
                        'account': result[0][0],
                    }
                else:
                    posting = {
                        'account': conf.get('to', 'Expenses:Unkown')
                    }
                posting.update({'amount': amount * -1, 'currency': currency})
                transaction.add(**posting)

            print_results = True

            print(transaction.to_string(), '\n', file=sys.stderr)
            str_out += "```\n" + transaction.to_string() + "\n```\n"
            with open(conf['ledger_file'], 'a') as outfile:
                print(transaction.to_string() + '\n', file=outfile)

        if print_results:
            print('## Transactions for ' + account + '\n' + str_out, file=sys.stdout)


if __name__ == "__main__":
    automatic()
