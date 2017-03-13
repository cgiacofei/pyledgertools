"""Convert ledger-cli formatted plain text to python data structure."""

import re


def process_transaction(transaction):
    """Process Transaction."""
    print('Process Transaction')


def process_commodity_price(transaction):
    """Process Commodity Price."""
    print('Process Commodity Price')


def process_budget(transaction):
    """Process Budget Entry."""
    print('Process Budget Entry')


def process_automated(transaction):
    """Process Automated Entry."""
    print('Process Automated Entry')


def import_journal(journal_string):
    """Main entry point for parsing ledger plaintext into python.

    See http://www.ledger-cli.org/3.0/doc/ledger3.html#Journal-Format for
    reference.

    """

    # This should be enough to split everything into a list of
    # plaintext transactions.
    blocks = journal_string.split('\n\n')

    # Remove comments and blank lines.
    # Convert transactions to list of lines.

    journal = []

    for idx, t in enumerate(blocks):
        t = t.split('\n')
        blocks[idx] = [x for x in t if x != '' and not x.startswith(';')]

        # Classify the transaction

        # Is tranasaction
        if re.match('^\d+', blocks[idx][0]) != None:
            journal.append(process_transaction(blocks[idx]))

        elif re.match('^P', blocks[idx][0]) != None:
             journal.append(process_commodity_price(blocks[idx]))

        elif re.match('^~', blocks[idx][0]) != None:
             journal.append(process_budget(blocks[idx]))

        elif re.match('^=', blocks[idx][0]) != None:
             journal.append(process_automated(blocks[idx]))
