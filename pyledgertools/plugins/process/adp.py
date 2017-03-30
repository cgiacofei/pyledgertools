"""Process ADP paystub json."""
import glob
import os
from yapsy.IPlugin import IPlugin


class ProcessADP(object):
    """Main ADP paycheck parser class."""

    def __init__(self, config):
        self.stub_dir = config['global']['paystubs']

    def get_transaction(self):
        pass

    def _lookup_stub(self, transaction):
        """Match paystub with transaction."""

        glob_dir = os.path.join([self.stub_dir, '**', '*.json'])
        for json_file in glob.iglob(glob_dir, recursive=True):
            pass
            # Do processing

    def _parse_stub(self, stub_json):
        pas
