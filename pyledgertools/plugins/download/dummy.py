
from yapsy.IPlugin import IPlugin

class DummyDownload(IPlugin):
    def download(self):
        """This would generate a file then return the filepath."""
        return 'budget/ofxfiles/suntrust_20170315.qfx'
