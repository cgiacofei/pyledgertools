"""Convert ledger-cli formatted plain text to python data structure."""

import re

DOLLAR_REGEX = '([\$A_Z]+) ([\-0-9]+.[0-9]{2,2})'

# Allocation RegEx
ALLOC_REGEX = '\s+([A-Za-z0-9:_]* ?[A-Za-z0-9:_]*)\s{2,}' + DOLLAR_REGEX
TRANS_REGEX = '^\d{4,4}-\d{2,2}-\d{2,2}\s+[!\*]?\s?(?P<payee>[\w\s]+)'


def train_journal(journal_string):
    """Generate training data from ledger entries."""

    blocks = [x.split('\n') for x in journal_string.split('\n\n')]

    training_data = []

    for tran in blocks:
        row = {}
        tran = [x for x in tran if x != '' and not x.startswith(';')]

        if len(tran) > 0:
            result = re.search(TRANS_REGEX, tran[0])
            if result:
                payee = result.group('payee')
                row['payee'] = payee

            result = re.findall(ALLOC_REGEX, ' '.join(tran[1:]))

            if len(result) > 0:
                row['account'], row['commodity'], row['amount'] = result[-1]

            if row:
                training_data.append(row)

    return training_data

with open('../tests/data/sample.ledger') as journal:
    journal_string = journal.read()

print(train_journal(journal_string))
