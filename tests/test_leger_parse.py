
from pyledgertools import ledger2python
from pyledgertools.ofx2ledger import Transaction

from nose.tools import assert_equal, assert_true
import os

dir = os.path.dirname(os.path.realpath(__file__))


class TestParseLedgerData:

    def setUp(self):
        with open(os.path.join(dir,'data','test.ledger')) as l_file:
            self.data = l_file.read()
            self.journal = ledger2python.import_journal(self.data)

    def test_load_tranasaction(self):
        """Journal file loaded as list of transaction objects."""

        assert_true(isinstance(self.journal, list))

        for entry in self.jounal:
            assert_true(isinstance(entry, Transaction))


