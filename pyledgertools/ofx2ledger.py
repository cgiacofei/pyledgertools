#! /usr/bin/env python3
"""OFX file parsing."""

from __future__ import print_function

from configparser import NoOptionError
from datetime import datetime
import hashlib
from ofxtools import OFXTree
import sys

from pyledgertools.journal import Transaction, Posting





def build_journal(ofx_file, config_accts):
    """Accept an ofx file and parse into list of Tansaction objects."""

    tree = OFXTree()
    tree.parse(ofx_file)
    ofx_obj = tree.convert()

    balance_assertions = []
    transactions = []

    # There may be multiple bank statements in one file
    for statement in ofx_obj.statements:

        routing = statement.account.bankid
        account = statement.account.acctid
        currency = CURRENCY_LOOKUP[statement.currency]
        balance = statement.ledgerbal.balamt
        stmnt_date = strftime(statement.ledgerbal.dtasof, '%Y-%m-%d')

        acct_options = find_in_config(config_accts, 'acctnum', account)

        a_assert = Posting(
            account=acct_options['from'],
            amount=balance,
            currency=currency,
            assertion=True
        )

        t_assert = Transaction(
            date=stmnt_date,
            payee='Balance for {}-{}'.format(ofx_obj.sonrs.org, account),
            postings=[a_assert]
        )

        balance_assertions.append(t_assert)

        for transaction in statement.transactions:
            meta = []

            payee = transaction.name
            amount = transaction.trnamt
            trn_date = strftime(transaction.dtposted, '%Y-%m-%d')
            trn_id = transaction.refnum

            # If check number is available add it as metadata
            check = transaction.checknum
            if check:
                meta.append(('check', transaction.checknum))

            # Build md5 Hash of transaction
            check_hash = trn_id + trn_date + payee + str(amount)
            hash_obj = hashlib.md5(check_hash.encode())
            meta.append(('UUID', hash_obj.hexdigest()))
            meta.append(('ImportDate', strftime(now(), '%Y-%m-%d')))

            a_tran = Posting(
                account=acct_options['from'],
                amount=amount
            )

            t_tran = Transaction(
                date=trn_date,
                payee=payee,
                postings=[a_tran],
                metadata=meta,
                account=account
            )

            # Need to process transactions further here
            # Either rules or Bayesian...

            transactions.append(t_tran)

    return balance_assertions, transactions


def find_in_config(config, key, value):
    """Find an item in a list of dicts.

    Parameters:
        config (ConfigParser): ConfigParser object to search.
        key (str): String value of the :obj:`dict` key to search.
        value (str): Value to search for.
    """

    for section in config.sections():
        try:
            if config.get(section=section, option=key) == value:
                return dict(config.items(section))
        except NoOptionError:
            pass

    return None


def export_journal(balances, transactions, **kwargs):
    """Send journal to files/screen.

    Parameters:
        balanes (list): List of :obj:`Transaction` objects containing
            :obj:`Posting` objects with `assertion` flag set to ``True``.
        transactions (list): :obj:`Transaction` objects to export.

    Keyword Args:
        output (str): Where to print output. Valid values are 'stdout' or
            'file', or any string that will be taken as a file name.

            A value of file sends to a preconfigured filename derived from the
            account ID. If a file name is given all output for all parsed
            accounts will be appended to this single file.
        assert_file (str): Filename to send balance asertions to or `None`
            for no assertions
    """

    output = kwargs.get('output', 'stdout')
    assert_file = kwargs.get('assert_file', 'bal.ledger')

    for transaction in transactions:
        if output == 'file':
            # Make this formattable?
            out_file = transaction.account + '.ledger'
        elif output == 'stdout':
            out_file = sys.stdout
        else:
            out_file = output

        print(transaction.to_string(), file=out_file)
        print('', file=out_file)

    if assert_file:
        for balance in balances:
            if output == 'file':
                out_file = assert_file
            else:
                out_file = sys.stdout

            print(balance.to_string(), file=out_file)
            print('', file=out_file)

