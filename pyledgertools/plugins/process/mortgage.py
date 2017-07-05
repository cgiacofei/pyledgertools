"""Get mortgage allocation from amortization schedule."""

from datetime import datetime
from yapsy.IPlugin import IPlugin
import csv

from pyledgertools.journal import Transaction, Posting

now = datetime.now
strftime = datetime.strftime
strptime = datetime.strptime

class AmortSchedule(IPlugin):
    """OFX file parsing."""

    def process(self, transaction, config, **args):
        """Get matching line from schedule.

        args: arguments from rules fils
            file: mortgage schedule csv file.
            <csv_column>: <ledger:account:name>
        """
        date = transaction.date

        schedule_csv = args.pop('file', None)
        currency = args.pop('currency', '$')

        with open(schedule_csv, 'r') as f:
            schedule = csv.DictReader(f)
            row = min(list(schedule), key=lambda x: abs(strptime(x['date'], '%Y-%m-%d') - date))

        running_sum = 0
        for column in args.keys():
            try:
                transaction.add(args[column], row[column], currency)
                sum += float(row[column])
            except KeyError:
                # If column is not in csv file use the remaining total balance.
                # This must happen last and only ONCE per transaction.
                value = transaction.postings[0].amount - running_sum
                transaction.add(args[column], value, currency)

        return transaction
