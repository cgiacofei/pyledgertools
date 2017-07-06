"""Get mortgage allocation from amortization schedule."""

from datetime import datetime
from yapsy.IPlugin import IPlugin
import csv
import logging
import logging.config

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
        self.config = config

        logging.config.dictConfig(config.get('logging', None))
        self.logger = logging.getLogger(__name__)

        date = transaction.date
        self.logger.info(
            'Transaction date: {}'.format(strftime(date, '%Y-%m-%d'))
        )
        schedule_csv = args.pop('file', None)
        currency = args.pop('currency', '$')

        with open(schedule_csv, 'r') as f:
            schedule = csv.DictReader(f)
            row = min(
                list(schedule),
                key=lambda x: abs(strptime(x['date'], '%Y-%m-%d') - date)
            )
            self.logger.info('Selected amortization row. ' + str(row))

        running_sum = 0
        for column in args.keys():
            try:
                transaction.add(args[column], row[column], currency)
                running_sum += float(row[column])
                self.logger.info(
                    'Add posting: {} {}'.format(args[column], row[column])
                )
            except KeyError:
                # If column is not in csv file use the remaining total balance.
                # This must happen last and only ONCE per transaction.
                value = transaction.postings[0].amount - running_sum
                transaction.add(args[column], value, currency)
                self.logger.info(
                    'Add posting: {} {}'.format(args[column], value)
                )

        return transaction
