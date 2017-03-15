"""Convert ledger-cli formatted plain text to python data structure."""

from itertools import groupby
from math import gcd
from operator import itemgetter
import re

DOLLAR_REGEX = '([\$A_Z]+) ([\-0-9]+.[0-9]{2,2})'

# Allocation RegEx
ALLOC_REGEX = '\s+([A-Za-z0-9:_]* ?[A-Za-z0-9:_]*)\s{2,}' + DOLLAR_REGEX
TRANS_REGEX = '^\d{4,4}-\d{2,2}-\d{2,2}\s+[!\*]?\s?(?P<payee>[&#\w\s]+)'


def GCD(dollars):
    """Find greatest common divisor of list of dollar ammounts."""

    # Convert dollar values to integers
    dollars = [int(d * 100) for d in dollars]

    res = dollars[0]

    for c in dollars[1::]:
        res = gcd(res , c)

    return res / 100


def train_journal(journal_string):
    """Generate training data from ledger entries."""

    blocks = [x.split('\n') for x in journal_string.split('\n\n')]

    training_data = []

    for tran in blocks:
        tran = [x for x in tran if x != '' and not x.startswith(';')]

        if len(tran) > 0:
            result = re.search(TRANS_REGEX, tran[0])
            if result:
                payee = result.group('payee')

            result = re.findall(ALLOC_REGEX, ' '.join(tran[1:]))

            if len(result) > 0:
                alloc_list = list(result[-1])
                alloc_list[2] = float(alloc_list[2])
                alloc_list[0] = alloc_list[0].strip()

                training_data.append([payee] + alloc_list)

    sorted_data = sorted(training_data, key=itemgetter(1))
    sorted_data = groupby(sorted_data, itemgetter(1))
    
    return_data = []
    for elmnt, items in sorted_data:
        grp_tran = [v for v in items]
        return_data.append([elmnt, grp_tran, GCD([v[3] for v in grp_tran])])

    return return_data


if __name__ == '__main__':

    with open('../tests/data/sample.ledger') as journal:
        journal_string = journal.read()

    data = train_journal(journal_string)
    
    for group in data:
        print('*** ', group[0], ' ***')
        for t in group[1]:
            print(t)
        print('Divisor',group[2])
        print('')

