#! /usr/bin/env python3
from __future__ import print_function

from datetime import datetime
import hashlib
from ofxtools import OFXTree
from operator import itemgetter
from optparse import OptionParser
import os
import re
from subprocess import call, Popen, PIPE
import sys
import time
import yaml
from yaml import load

from rule_parser import walk_rules, build_rules, make_rule

now = datetime.now
strftime = datetime.strftime

parser = OptionParser()

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

(options, args) = parser.parse_args()

TRANSACTION = (
    '{date}{c}{payee} {desc}'
    '{md5hash}{allocations}{tags}'
)

ALLOC_STR = '\n{indent}{account}{space} {commodity} {amount:0.2f}'
ASSERT_STR = '\n{indent}{account}{space} = {commodity} {amount:0.2f}'

FIELDS = {
    'PAYEE': 1,
    'HASH': 3,
    'AMOUNT': 2,
    'DATE': 0,
}


class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def make_tag_string(tags, indent):
    t = ':'.join([x for x in tags])
    return '{}; :{}:'.format(indent, t)


def make_meta_string(metadata, indent):
    m = []
    for meta in metadata:
        m.append('{}; {}: {}'.format(indent, meta[0], meta[1]))

    return '\n'.join(m)


class Allocation():
    """Allocation class for transactions."""

    def __init__(self, **kwargs):
        self.account = kwargs['account']
        self.amount = kwargs['amount']
        self.currency = kwargs.get('currency', '$')
        self.assertion = kwargs.get('assertion', False)
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])

    def to_string(self, width=80, indent=4):
        """ Allocation as string.
            fix to width in this.
        """

        ind = ' ' * indent
        acct = self.account
        if self.assertion:
            amt = '= {} {:.2f}'.format(self.currency, self.amount)
        else:
            amt = '{} {:.2f}'.format(self.currency, self.amount)
        
        fill = ' ' * (width - len(acct + amt + ind))

        outlist = []
        outlist.append(ind + acct + fill + amt)

        if len(self.tags) > 0:
            outlist.append(make_tag_string(self.tags, ind * 2))

        if len(self.metadata) > 0:
            outlist.append(make_meta_string(self.metadata, ind * 2))

        return '\n'.join(outlist)


class Transaction():
    """Class for managing transactions."""

    def __init__(self, **kwargs):
        self.date = kwargs['date']
        self.flag = kwargs.get('flag', ' ')
        self.payee = kwargs['payee']
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])
        self.allocations = kwargs.get('allocations', [])
        self.bankid = kwargs.get('bankid', None)
        self.acctid = kwargs.get('acctid', None)

    def to_string(self, width=80, indent=4):
        """Transaction to string."""
        ind = ' ' * indent

        outlist = []

        top_row = '{} {} {}'.format(
            self.date,
            self.flag,
            self.payee
        )

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
            account = acct_options['ledger_from'],
            amount = balance,
            assertion = True
        )

        t_assert = Transaction(
            date = stmnt_date,
            payee = 'Balance for {}-{}'.format(ofx_obj.sonrs.org, account),
            allocations = [a_assert]
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
                account = acct_options['ledger_from'],
                amount = amount
            )

            t_tran = Transaction(
                date = trn_date,
                payee = payee,
                allocations = [a_tran],
                metadata = meta
            )

            # Need to process transactions further here
            # Either rules or Bayesian...

            transactions.append(t_tran)
    

    return balance_assertions, transactions


def find_in_config(config_list, key, value):
    """Find an item in a list of dicts."""

    for item in config_list:
        if item[key] == value:
            return item


def process_ofx(config_accounts, ofx_file=None):
    if ofx_file:
        with open(ofx_file, 'r') as ofx_file:
            ofx = OfxParser.parse(ofx_file)
    else:
        # Run OFX download
        call(['ofxclient', '--download', 'banks.ofx'])
        with open('banks.ofx', 'r') as ofx_file:
            ofx = OfxParser.parse(ofx_file)

    # Parse the file into a dictionary object
    parsed_accounts = parse_ofx(ofx)

    rule_dict = build_rules(options.rule_file)

    assert_list = []
    for account in parsed_accounts.keys():
        data = find_in_config(config_accounts, 'account_id', account)

        account_string = data['ledger_from']
        default_account = data['ledger_to']

        transactions = parsed_accounts[account]['trans']
        for rule, trans_obj in check_transactions(transactions, rule_dict):
            # Check additional tags in rule
            try:
                skip = rule_dict[rule]['Ignore']
            except:
                skip = False

            try:
                if rule_dict[rule]['Change_Payee'] == 'True':
                    trans_obj['payee'] = rule
            except KeyError:
                if rule is not False:
                    trans_obj['payee'] = rule

            outfile = os.path.join('dat','{}.ledger'.format(account))
            if rule and not skip:
                with open(outfile, 'a') as oFile:
                    print('', file=oFile)
                    print_transaction(
                        trans_obj,
                        rule_dict[rule],
                        account_string,
                        clr=True,
                        outfile=oFile
                    )

            elif not skip:
                payee = trans_obj['payee']
                new_rule = make_rule(payee, default_account)
                with open(outfile,'a') as oFile:
                    print('', file=oFile)
                    print_transaction(
                        trans_obj,
                        new_rule,
                        account_string,
                        clr=False,
                        outfile=oFile
                    )

                with open(outfile.replace('dat','un'), 'a') as oFile:
                    print('', file=oFile)
                    print_transaction(
                        trans_obj,
                        new_rule,
                        account_string,
                        clr=False,
                        outfile=oFile
                    )

        balance = {
            'amount': parsed_accounts[account]['balance'],
            'payee': 'Balance Assertion',
            'date': strftime(now(), '%Y-%m-%d')
        }

        with open(os.path.join('dat','Budget.ledger'), 'a') as oFile:
            print('', file=oFile)
            print_transaction(
                balance,
                None,
                account_string,
                outfile=oFile
            )


def check_transactions(transaction, rules):

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


if __name__ == "__main__":
    if options.config:
        c_path = options.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(ROOT, 'ofx.conf')

    config = load(open(c_path, 'r'))

    build_journal(options.ofx_file, config['accounts'])
