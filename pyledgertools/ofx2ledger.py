#! /usr/bin/env python3
from __future__ import print_function

from datetime import datetime
import hashlib
from ofxtools import OFXTree
import os
import sys

from pyledgertools.rule_parser import walk_rules, build_rules, make_rule

now = datetime.now
strftime = datetime.strftime


def make_tag_string(tags, indent):
    t = ':'.join([x for x in tags])
    return '{}; :{}:'.format(indent, t)


def make_meta_string(metadata, indent):
    """Convert list of metadata lists into a string.

    Parameters:
        metadata (list): List of list pairs (key, value)
        indent (str): String used for indentation.

    Returns:
        str: Returns a metadata string suitable for a ledger-cli journal.

    >>> make_meta_string([['key1', 'value1'], ['key2', 'value2']], '  ')
    "  ; key1: value1\\n  ; key2: value2"
    """
    m = []
    for meta in metadata:
        m.append('{}; {}: {}'.format(indent, meta[0], meta[1]))

    return '\n'.join(m)


class Allocation(object):
    """Allocation class for transactions.

    Attributes:
        account (str): Name of the ledger account for this allocation.
        amount (float): Dollar value of the allocation.
        currency (str): String representing the allocation commodity.
            ``$``, ``USD``, ``CAN`` etc.
        assertion (bool): Set to `True` if allocation is a balance assertion.
            Allocation will be represented as:
            ::

            <account>                                      = <currency> <amount>

            Instead of:
            ::

            <account>                                        <currency> <amount>
        tags (list): Tag strings to add to the allocation.
        metadata (list): Key/value pairs to add to allocation.
    """

    def __init__(self, **kwargs):
        """Initialize allocation.

        Parameters:
            account (str): Name of the ledger account for this allocation.
            amount (float): Dollar value of the allocation.
            currency (str): String representing the allocation commodity.
            assertion (bool): Set to 'True' if allocation is balance assertion.
            tags (list): Tag strings to add to the allocation.
            metadata (list): Key/value pairs to add to allocation.
        """
        self.account = kwargs['account']
        self.amount = kwargs['amount']
        self.currency = kwargs.get('currency', '$')
        self.assertion = kwargs.get('assertion', False)
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])

    def to_string(self, width=80, indent=4):
        """ Allocation as string. Fix to width in this.

        Keyword Args:
            width (int): White space added after allocation acount to align last
                digit of 'amount' to column `width`.
            indent (int): Number of spaces to indent each level of transaction.

        Return:
            str: Ledger-cli formatted string for the allocation.
        """

        ind = ' ' * indent
        acct = self.account
        if self.assertion:
            amt = '= {} {:.2f}'.format(self.currency, self.amount)
        else:
            amt = '{} {:.2f}'.format(self.currency, self.amount)

        # Calculate fill, split amount at decimal to align to decimal.
        fill = ' ' * (width - len(acct + amt.split('.')[0] + ind + 3))

        outlist = []
        outlist.append(ind + acct + fill + amt)

        if len(self.tags) > 0:
            outlist.append(make_tag_string(self.tags, ind * 2))

        if len(self.metadata) > 0:
            outlist.append(make_meta_string(self.metadata, ind * 2))

        return '\n'.join(outlist)


class Transaction(object):
    """Class for managing transactions.

    Attributes:
        date (str): Transaction date.
        flag (str): Flag to mark transaction as cleared ' * ' or pending ' ! '
        payee (str): Transaction payee value.
        tags (list): List of tags to apply to the transaction
        metadata (list): Tags with values given as list of lists.
            ``[['key1', 'value1'], ['key2', 'value2']]``
        allocations (list): List of :obj:`Allocation` objects
        bankid (str):
        acctid (str):
        account (str):
    """

    def __init__(self, **kwargs):
        """Initialize Transaction object.

        Parameters:
            date (str): Transaction date.
            flag (str): Flag to mark transaction as cleared ' * '
                or pending ' ! '
            payee (str): Transaction payee value.
            tags (list): List of tags to apply to the transaction
            metadata (list): Tags with values given as list of lists.
                ``[['key1', 'value1'], ['key2', 'value2']]``
            allocations (list): List of :obj:`Allocation` objects
            bankid (str):
            acctid (str):
            account (str):
        """
        self.date = kwargs['date']
        self.flag = kwargs.get('flag', ' ')
        self.payee = kwargs['payee']
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])
        self.allocations = kwargs.get('allocations', [])
        self.bankid = kwargs.get('bankid', None)
        self.acctid = kwargs.get('acctid', None)
        self.account = kwargs.get('account', '')

    def to_string(self, width=80, indent=4):
        """Transaction to string.

        Keyword Args:
            width (int): Text column to align the end of each transaction
                line to.
            indent (int): Number of spaces to indent each level of transaction.

        Return:
            str: Ledger-cli formatted string for the entire transaction.
        """
        ind = ' ' * indent

        outlist = []

        top_row = self.date + self.flag + self.payee
        outlist.append(top_row)

        if len(self.tags) > 0:
            outlist.append(make_tag_string(self.tags, ind))

        if len(self.metadata) > 0:
            outlist.append(make_meta_string(self.metadata, ind))

        alloc = [a.to_string(indent=indent) for a in self.allocations]
        outlist.append('\n'.join(alloc))

        return '\n'.join(outlist)


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
        currency = statement.currency
        balance = statement.ledgerbal.balamt
        stmnt_date = strftime(statement.ledgerbal.dtasof, '%Y-%m-%d')

        acct_options = find_in_config(config_accts, 'account_id', account)

        a_assert = Allocation(
            account=acct_options['ledger_from'],
            amount=balance,
            assertion=True
        )

        t_assert = Transaction(
            date=stmnt_date,
            payee='Balance for {}-{}'.format(ofx_obj.sonrs.org, account),
            allocations=[a_assert]
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
            meta.append(('md5', hash_obj.hexdigest()))

            a_tran = Allocation(
                account=acct_options['ledger_from'],
                amount=amount
            )

            t_tran = Transaction(
                date=trn_date,
                payee=payee,
                allocations=[a_tran],
                metadata=meta,
                account=account
            )

            # Need to process transactions further here
            # Either rules or Bayesian...

            transactions.append(t_tran)

    return balance_assertions, transactions


def find_in_config(config_list, key, value):
    """Find an item in a list of dicts.

    Parameters:
        config_list (list): list of account configuration :obj:`dict`.
        key (str): String value of the :obj:`dict` key to search.
        value (str): Value to search for.

    """

    for item in config_list:
        if item[key] == value:
            return item


def export_journal(balances, transactions, **kwargs):
    """Send journal to files/screen.

    Parameters:
        balanes (list): List of :obj:`Transaction` objects containing 
            :obj:`Allocation` objects with the `assertion` flag set to ``True``.
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


def check_transactions(transaction, rules):
    """Check transaction against rules dict.

    Note:
        Currently not in use.
    """
    for trans in transaction:
        trans_dict = {}

        try:
            trans_dict['date'] = trans[FIELDS['DATE']]
        except:
            trans_dict['date'] = ''

        try:
            trans_dict['payee'] = trans[FIELDS['PAYEE']]
        except:
            trans_dict['payee'] = ''

        try:
            trans_dict['hash'] = trans[FIELDS['HASH']]
        except:
            trans_dict['hash'] = ''

        try:
            trans_dict['amount'] = trans[FIELDS['AMOUNT']]
        except:
            trans_dict['amount'] = ''

        for rule in rules.keys():
            # Get Root rule logic type
            root_rule = rules[rule]['Conditions'][0]
            logic, first_dict = list(root_rule.items())[0]

            match = walk_rules(first_dict, trans, logic)

            if match:
                match = rule
                break

        yield match, trans_dict
