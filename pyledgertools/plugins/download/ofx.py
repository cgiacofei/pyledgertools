"""OFX downloader."""

from ofxtools.Client import OFXClient, BankAcct
from ofxtools.Types import DateTime
from yapsy.IPlugin import IPlugin


def make_date_kwargs(config):
    return {k:DateTime().convert(v) for k,v in config.items() if k.startswith('dt')}


class OFXDownload(IPlugin):
    """OFX plugin class."""

    def download(self, config):
        """Setup account info and credentials."""

        client = OFXClient(
            config['url'],
            config['org'],
            config['fid'],
            version=config['version'],
            appid=config['appid'],
            appver=config['appver']
        )

        account = [BankAcct(config['fid'], config['acctnum'], config['type'])]
        kwargs = make_date_kwargs(config)

        request = client.statement_request(
            config['ofxuser'],
            config['ofxpswd'],
            account,
            **kwargs
        )

        response = client.download(request)
        fname = '{}_{}.ofx'.format(config['fid'], config['acctnum']) 
        with open(fname, 'w') as ofxfile:
            print(response.text, file=ofxfile)

        return fname
