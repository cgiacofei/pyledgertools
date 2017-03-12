import os

from pyledgertools import ofx2ledger
from nose.tools import assert_equal, assert_true

dir = os.path.dirname(os.path.realpath(__file__))


class TestSuntrustOFX:

    def setUp(self):
        ofx_data = os.path.join(dir, 'data', 'suntrust.qfx')

        self.config = [
            {
                'account_id':  '0123456789',
                'ledger_from': 'Assets:Banks:CapOne:Checking:84639370',
                'ledger_to':   'Expenses:Flex:General',
            }
        ]

        self.bal, self.tran = ofx2ledger.build_journal(ofx_data, self.config)
        self.assertion = self.bal[0]

    def test_transaction_count(self):
        """Check number of transactions for each list."""

        assert_equal(len(self.bal),  1)
        assert_equal(len(self.tran), 16)

    def test_statement_date(self):
        """Test for correct statement date."""

        assert_equal(self.assertion.date, '2017-03-04')

    def test_assertion_properties(self):
        """Check balance assertion transaction properties.

        Should only contain one allocation.
        The 'assertion' flag should be set to True.
        """

        assert_equal(len(self.assertion.allocations), 1)
        assert_true(self.assertion.allocations[0].assertion)

    def test_statement_balance(self):
        """Check for correct statement balance."""

        b_alloc = self.assertion.allocations[0]
        assert_equal(b_alloc.amount, 1425.59)

    def test_transaction_balance(self):
        """Transaction allocations should sum to zero."""

        for transaction in self.tran:
            assert_equal(sum([x.amount for x in transaction.allocations]), 0)
