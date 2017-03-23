#! /usr/bin/env python3
"""OFX file parsing."""

from __future__ import print_function

from datetime import datetime


now = datetime.now
strftime = datetime.strftime


def make_tag_string(tags, indent):
    t = ':'.join([x for x in tags])
    return '{}; :{}:'.format(indent, t)


def make_meta_string(metadata, indent):
    """Convert list of metadata lists into a string.

    Parameters:
        metadata (list): List of list pairs (key, value)
        indent (str): String used for indentation.

    Returns:
        str: Returns a metadata string suitable for a ledger-cli journal.

    >>> make_meta_string([['key1', 'value1'], ['key2', 'value2']], '  ')
    "  ; key1: value1\\n  ; key2: value2"
    """
    m = []
    for meta in metadata:
        m.append('{}; {}: {}'.format(indent, meta[0], meta[1]))

    return '\n'.join(m)


class Posting(object):
    """Posting class for transactions.

    Attributes:
        account (str): Name of the ledger account for this posting.
        amount (float): Dollar value of the posting.
        currency (str): String representing the allocation commodity.
            ``$``, ``USD``, ``CAN`` etc.
        assertion (bool): Set to `True` if posting is a balance assertion.
            Allocation will be represented as:
            ::

            <account>                                      = <currency> <amount>

            Instead of:
            ::

            <account>                                        <currency> <amount>
        tags (list): Tag strings to add to the posting.
        metadata (list): Key/value pairs to add to posting.
    """

    def __init__(self, **kwargs):
        """Initialize allocation.

        Parameters:
            account (str): Name of the ledger account for this posting.
            amount (float): Dollar value of the posting.
            currency (str): String representing the allocation commodity.
            assertion (bool): Set to 'True' if posting is balance assertion.
            tags (list): Tag strings to add to the posting.
            metadata (list): Key/value pairs to add to posting.
        """
        self.account = kwargs['account']
        self.amount = kwargs['amount']
        self.currency = kwargs.get('currency', '$')
        self.assertion = kwargs.get('assertion', False)
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])

    def to_string(self, width=80, indent=4):
        """ Posting as string. Fix to width in this.

        Keyword Args:
            width (int): White space added after posting acount to align last
                digit of 'amount' to column `width`.
            indent (int): Number of spaces to indent each level of transaction.

        Return:
            str: Ledger-cli formatted string for the posting.
        """

        ind = ' ' * indent
        acct = self.account
        if self.assertion:
            amt = '= {} {:.2f}'.format(self.currency, self.amount)
        else:
            amt = '{} {:.2f}'.format(self.currency, self.amount)

        # Calculate fill, split amount at decimal to align to decimal.
        fill = ' ' * (width - len(acct + amt.split('.')[0] + ind) - 3)

        outlist = []
        outlist.append(ind + acct + fill + amt)

        if len(self.tags) > 0:
            outlist.append(make_tag_string(self.tags, ind * 2))

        if len(self.metadata) > 0:
            outlist.append(make_meta_string(self.metadata, ind * 2))

        return '\n'.join(outlist)


class Transaction(object):
    """Class for managing transactions.

    Attributes:
        date (str): Transaction date.
        flag (str): Flag to mark transaction as cleared ' * ' or pending ' ! '
        payee (str): Transaction payee value.
        tags (list): List of tags to apply to the transaction
        metadata (list): Tags with values given as list of lists.
            ``[['key1', 'value1'], ['key2', 'value2']]``
        postings (list): List of :obj:`Posting` objects
        bankid (str):
        acctid (str):
        account (str):
    """

    def __init__(self, **kwargs):
        """Initialize Transaction object.

        Parameters:
            date (str): Transaction date.
            flag (str): Flag to mark transaction as cleared ' * '
                or pending ' ! '
            payee (str): Transaction payee value.
            tags (list): List of tags to apply to the transaction
            metadata (list): Tags with values given as list of lists.
                ``[['key1', 'value1'], ['key2', 'value2']]``
            postings (list): List of :obj:`Posting` objects
            bankid (str):
            acctid (str):
            account (str):
        """
        self.date = kwargs['date']
        self.flag = kwargs.get('flag', ' ')
        self.payee = kwargs['payee']
        self.tags = kwargs.get('tags', [])
        self.metadata = kwargs.get('metadata', [])
        self.postings = kwargs.get('postings', [])
        self.bankid = kwargs.get('bankid', None)
        self.acctid = kwargs.get('acctid', None)
        self.account = kwargs.get('account', '')
        self.uuid = kwargs.get('uuid', '')

    def to_string(self, width=80, indent=4):
        """Transaction to string.

        Keyword Args:
            width (int): Text column to align the end of each transaction
                line to.
            indent (int): Number of spaces to indent each level of transaction.

        Return:
            str: Ledger-cli formatted string for the entire transaction.
        """
        ind = ' ' * indent

        outlist = []

        top_row = self.date + self.flag + self.payee
        outlist.append(top_row)

        if len(self.tags) > 0:
            outlist.append(make_tag_string(self.tags, ind))

        if len(self.metadata) > 0:
            outlist.append(make_meta_string(self.metadata, ind))

        postings = [a.to_string(indent=indent) for a in self.postings]
        outlist.append('\n'.join(postings))

        return '\n'.join(outlist)

    def add(self, account, amount, currency):
        """Add a posting to a transaction.

        Parameters:
            account (str): Name of the ledger account for this posting.
            amount (float): Dollar value of the allocation.
            currency (str): String representing the posting commodity.
        """
        new_posting = Posting(
            account=account,
            amount=amount,
            currency=currency
        )

        self.postings.append(new_posting)
