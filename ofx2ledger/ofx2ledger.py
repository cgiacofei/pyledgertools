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


def build_rules(rule_loc):
    """Build rules from file or directory."""
    if os.path.isfile(rule_loc):
        rules = load(open(rule_loc))

    # If directory is given find all .rules files in directory
    # and build a single dictionary from their contents.
    elif os.path.isdir(rule_loc):
        rules = {}
        for root, dirs, files in os.walk(rule_loc):
            for file in files:
                if file.endswith('.rules'):
                    rules.update(load(open(os.path.join(root, file))))

    return rules


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


def parse_ofx(ofx_obj, delim='\t'):
    account_dict = {}

    for account in ofx_obj.accounts:
        trans_objs = []
        hashes = ''

        if account.number not in account_dict:
            account_dict[account.number] = {}
            balance = account.statement.balance
            account_dict[account.number]['balance'] = balance

        if len(account.statement.transactions) > 0:
            for transaction in account.statement.transactions:
                date = strftime(transaction.date, '%Y-%m-%d')
                payee = transaction.payee.strip(',')
                amount = str(transaction.amount)

                trans_line = [date, payee, amount]

                # Check that the trans_obj signature is not already present
                check_hash = '{}{}{}{}'.format(
                    transaction.id,
                    transaction.date,
                    transaction.payee,
                    transaction.amount
                )
                hash_obj = hashlib.md5(check_hash.encode())
                md5_hash = hash_obj.hexdigest()
                trans_line.append(md5_hash)

                # Only if ledger file is given
                if options.ledger_file:
                    ledger_cmd = ['ledger',
                                  '-f', options.ledger_file,
                                  'reg', '%md5=' + md5_hash]
                    process = Popen(ledger_cmd, stdout=PIPE, stderr=PIPE)
                    result, stderr = process.communicate()
                else:
                    result = b''
                    stderr = b''

                # Check for trans_obj signature in hash file
                if result.decode('ascii') == '':
                    trans_objs.append(trans_line)

            # Sort trans_objs by date and add to dictionary
            trans_objs = sorted(trans_objs, key=itemgetter(0))
            account_dict[account.number]['trans'] = trans_objs
            account_dict[account.number]['hash'] = hashes

    return account_dict


def new_process_ofx(ofx_files):
    """Accept list of ofx files and process them."""

    # balance_list = []

    # For each ofx file
        # For each account in file
            #~ route = account.routing_number
            #~ num = account_id
            #~ output_filename = '{}_{}.ledger'.formt(route, num)

            # Process statement trans_objs
                # Calculate trans_obj hash
                # Check againt rules
                # Print the trans_obj now or wait?
            #~ balance_list.append( statement balance )

    pass


# Comparison functions
# Dates used as strings in format YYYY-MM-DD so string comparison can be used
def CONTAINS(rule_value, tran_value):
    """Return True if rule_value contained in tran_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    return tran_value.find(rule_value) >= 0


def STARTS_WITH(rule_value, tran_value):
    """Return True if tran_value starts with rule_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    tran_value = tran_value.strip()
    return tran_value.startswith(rule_value)


def ENDS_WITH(rule_value, tran_value):
    """Return True if tran_value ends with rule_value
    """

    rule_value = rule_value.lower()
    tran_value = tran_value.lower()

    tran_value = tran_value.strip()
    return tran_value.endswith(rule_value)


def EQUALS(rule_value, tran_value):
    """Return True if rule_value is euqal to tran_value.  Works for both
    numbers and strings
    """

    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value == tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        tran_value = tran_value.strip()

        return rule_value == tran_value


def GT(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value < tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value < tran_value


def GE(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value <= tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value <= tran_value


def LT(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value > tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value > tran_value


def LE(rule_value, tran_value):
    try:
        rule_value = float(rule_value)
        tran_value = float(tran_value)
        return rule_value >= tran_value
    except ValueError:
        rule_value = rule_value.lower()
        tran_value = tran_value.lower()
        return rule_value >= tran_value


def MOD(rule_value, tran_value):
    modulus = float(tran_value) % float(rule_value)

    if modulus == 0:
        return True

    return False


def check_condition(condition, trans_obj):
    """Convert the condition string from the rule into the
    appropriate function and evaluate it.
    """
    condition = condition.split(' ')

    field = condition[0]
    test = condition[1]
    test_value = ' '.join(condition[2:])

    # Use string value to access comparison function
    # sys.module[__name__] returns this module
    test_func = getattr(sys.modules[__name__], test)

    try:
        field_value = trans_obj[FIELDS[field]]
    except:
        field_value = ''

    return test_func(test_value, field_value)


# Boolean logic functions
def AND(bools):
    """Logical And."""
    if False in bools:
        return False

    return True


def OR(bools):
    """Logical OR."""
    if True in bools:
        return True

    return False


def NAND(bools):
    return not AND(bools)


def NOR(bools):
    return not OR(bools)


def XOR(bools):
    """Logical Xor.
       Result is True if there are an odd number of true items
       and False if there are an even number of true items.
    """
    # Return false if there are an even number of True results.
    if len([x for x in bools if x == True]) % 2 == 0:
        return False

    return True


def walk_rules(conditions, trans_obj=None, logic=None):
    results = []

    for condition in conditions:
        if isinstance(condition, dict):
            new_logic = list(condition.keys())[0]
            res = walk_rules(condition[new_logic], trans_obj, new_logic)
        if isinstance(condition, str):
            res = check_condition(condition, trans_obj)

        results.append(res)

    # Evaluate results
    l_func = getattr(sys.modules[__name__], logic)
    final = l_func(results)

    return final


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


def print_transaction(trans_obj, rule, account, outfile=sys.stdout, clr=False):

    allocations = ''

    trans_total = float(trans_obj['amount'])

    if rule:
        # Build list of tags
        tag_list = ''
        try:
            for tag in rule['Tags']:
                tag_list = tag_list.join('      ; {}\n'.format(tag))
        except:
            pass

        main_allocation = ALLOC_STR.format_map(SafeDict(
            indent='    ',
            account=account,
            amount=trans_total,
            commodity='$',
        ))

        allocations += main_allocation.format(
            space=' ' * (80 - len(main_allocation) + 8)
        )

        alloc_total = 0

        for allocation in rule['Allocations']:
            a_list = allocation.split(' ')

            val = int(a_list[0])
            typ = a_list[1]
            acct = ' '.join(a_list[2:])

            if typ == 'PERCENT':
                amount = trans_total * val * .01
                # Make sure we haven't overshot
                if abs(amount + alloc_total) > abs(trans_total):
                    amount = trans_total - alloc_total

            elif typ == 'DOLLARS':
                if abs(val + alloc_total) > abs(trans_total):
                    amount = trans_total - alloc_total
                else:
                    amount = val

            elif typ == 'REMAINDER':
                if abs(trans_total) > abs(alloc_total):
                    amount = trans_total - alloc_total
                else:
                    amount = 0

            alloc_total += amount

            if amount != 0:
                match_allocation = ALLOC_STR.format_map(SafeDict(
                    indent='    ',
                    account=acct,
                    amount=amount * -1,
                    commodity='$',

                ))
                allocations += match_allocation.format(
                    space=' ' * (80 - len(match_allocation) + 8)
                )
        md5 = '\n    ; md5: {}'.format(trans_obj['hash'])
    else:
        md5 = ''
        allocations = ASSERT_STR.format_map(SafeDict(
            indent='    ',
            account=account,
            amount=trans_total,
            commodity='$',
        ))
        allocations = allocations.format(
                    space=' ' * (80 - len(allocations) + 8)
                )

    if clr:
        c_char = ' * '
    else:
        c_char = '  '

    print_out = TRANSACTION.format(
        md5hash=md5,
        date=trans_obj['date'],
        payee=trans_obj['payee'],
        desc='',
        allocations=allocations,
        tags='',
        c=c_char
    )

    print(print_out, file=outfile)


def make_rule(payee, account):
    payee = re.sub('[^a-zA-Z0-9 \n\.,]', '', payee)

    rule_template = """---
        '{name}':
          Change_Payee: False
          Conditions:
            - AND:
              - PAYEE CONTAINS {payee}
          Allocations:
            - 100 PERCENT {account}
        """
    rule_string = rule_template.format(
        name=payee,
        payee=payee,
        account=account
    )

    rule_yml = yaml.load(rule_string)

    return rule_yml[payee]


if __name__ == "__main__":
    if options.config:
        c_path = options.config

    else:
        ROOT = os.path.dirname(os.path.realpath(__file__))
        c_path = os.path.join(ROOT, 'ofx.conf')

    config = load(open(c_path, 'r'))

    build_journal(options.ofx_file, config['accounts'])

    #~ process_ofx(
        #~ config['accounts'],
        #~ options.ofx_file
    #~ )
