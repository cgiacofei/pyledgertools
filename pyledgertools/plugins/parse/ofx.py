"""Parse ofx files into journal object."""

from datetime import datetime
import hashlib
from ofxtools import OFXTree
from yapsy.IPlugin import IPlugin

from pyledgertools.journal import Transaction, Posting

now = datetime.now
strftime = datetime.strftime
CURRENCY_LOOKUP = {
    'USD': '$',
}
"""Dictoinary for converting ofx currency string to a proper symbol."""


class ParseOFX(IPlugin):
    """OFX file parsing."""

    def __init__(self):
        self.is_activated = False

    def build_journal(self, ofx_file, config):
        tree = OFXTree()
        tree.parse(ofx_file)
        ofx_obj = tree.convert()

        balance_assertions = []
        transactions = []

        # There may be multiple bank statements in one file
        for statement in ofx_obj.statements:

            routing = statement.account.bankid
            account = statement.account.acctid
            currency = CURRENCY_LOOKUP[statement.currency]
            balance = statement.ledgerbal.balamt
            stmnt_date = strftime(statement.ledgerbal.dtasof, '%Y-%m-%d')

            a_assert = Posting(
                account=config['from'],
                amount=balance,
                currency=currency,
                assertion=True
            )

            t_assert = Transaction(
                date=stmnt_date,
                payee='Balance for {}-{}'.format(ofx_obj.sonrs.org, account),
                postings=[a_assert]
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
                meta.append(('UUID', hash_obj.hexdigest()))
                meta.append(('ImportDate', strftime(now(), '%Y-%m-%d')))

                a_tran = Posting(
                    account=config['from'],
                    amount=amount
                )

                t_tran = Transaction(
                    date=trn_date,
                    payee=payee,
                    postings=[a_tran],
                    metadata=meta,
                    account=account
                )

                # Need to process transactions further here
                # Either rules or Bayesian...

                transactions.append(t_tran)

        return balance_assertions, transactions
