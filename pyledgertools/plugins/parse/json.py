"""Parse json files into journal object."""

from datetime import datetime
import hashlib
from yapsy.IPlugin import IPlugin
import json
import re

from pyledgertools.journal import Transaction, Posting

now = datetime.now
strftime = datetime.strftime


class ParseJSON(IPlugin):
    """OFX file parsing."""

    def build_journal(self, json_file, config):
        with open(json_file, 'r') as jfile:
            json_data = json.load(jfile)

        transactions = []

        # There may be multiple bank statements in one file
        for transaction in json_data:
            meta = []

            payee = transaction['payee']
            currency = transaction['currency']
            amount = float(transaction['amount'])
            trn_date = transaction['date']

            # If check number is available add it as metadata
            check = re.match('CHECK\s+#(\d+)', payee)
            if check:
                meta.append(('check', check.group(0)))

            # Build md5 Hash of transaction
            check_hash = trn_date + payee + str(amount)
            hash_obj = hashlib.md5(check_hash.encode())
            uuid = hash_obj.hexdigest()
            meta.append(('UUID', uuid))
            meta.append(('Imported', strftime(now(), '%Y-%m-%d')))

            a_tran = Posting(
                account=config['from'],
                amount=amount,
                currency=currency
            )

            t_tran = Transaction(
                date=trn_date,
                payee=payee,
                postings=[a_tran],
                metadata=meta,
                uuid=uuid
            )

            transactions.append(t_tran)

        return None, transactions
