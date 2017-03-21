"""Parse ofx files into journal object."""
from yapsy.IPlugin import IPlugin

from pyledgertools.journal import Transaction, Posting


class ParseOFX(IPlugin):
    """OFX file parsing."""

    def __init__(self):
        self.is_activated = False

    def build_journal(self, csv_file, config):
        pass
