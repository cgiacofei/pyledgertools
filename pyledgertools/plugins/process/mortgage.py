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

    def process(self, transaction, config, rule_args):
        """Get matching line from schedule.

        rule_args: arguments from rules fils
            file: mortgage schedule csv file.
            currency: Currency to use for postings. (default to '$')
            <csv_column>: <ledger:account:name>
        """
        self.config = config
        logging.config.dictConfig(config.get('logging', None))
        self.logger = logging.getLogger(__name__)

        date = transaction.date
        self.logger.info(
            'Transaction date: {}'.format(date)
        )
        schedule_csv = rule_args.pop('file', None)
        currency = rule_args.pop('currency', '$')

        self.logger.info(
            'Reading schedule from {}'.format(schedule_csv)
        )
        with open(schedule_csv, 'r') as f:
            schedule = csv.DictReader(f)
            row = min(
                list(schedule),
                key=lambda x: abs(strptime(x['date'], '%Y-%m-%d') - strptime(date, '%Y-%m-%d'))
            )
            self.logger.debug('Selected amortization row. ' + str(row))

        running_sum = 0.00
        for column in rule_args.keys():
            try:
                row_value = float(row[column].replace('$', ''))
                transaction.add(rule_args[column], row_value, currency)
                running_sum += row_value
                self.logger.info(
                    'Add posting: {}  {} {}'.format(rule_args[column], currency, row_value)
                )
            except KeyError:
                # If column is not in csv file use the remaining total balance.
                # This must happen last and only ONCE per transaction.
                value = abs(transaction.postings[0].amount) - abs(running_sum)
                transaction.add(rule_args[column], value, currency)
                self.logger.info(
                    'Add posting: {} {}'.format(rule_args[column], value)
                )

        return transaction
