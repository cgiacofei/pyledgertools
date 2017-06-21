"""OFX downloader."""

from ofxtools.Client import OFXClient, StmtRq, InvStmtRq
from ofxtools.Types import DateTime
from yapsy.IPlugin import IPlugin


def make_date_kwargs(config):
    return {k:DateTime().convert(v) for k,v in config.items() if k.startswith('dt')}


class OFXDownload(IPlugin):
    """OFX plugin class."""

    def download(self, config):
        """Setup account info and credentials."""

        client = OFXClient(
            config.get('url', None),
            org=config.get('org', None),
            fid=config.get('fid', None),
            bankid=config.get('bankid', None),
            brokerid=config.get('brokerid', None),
            version=config.get('version', None),
            appid=config.get('appid', None),
            appver=config.get('appver', None)
        )

        try:
            stmtrq = StmtRq(acctid=config.get('checking', config['savings']))
        except:
            stmtrq = None

        try:
            invstmtrq = InvStmtRq(acctid=config['investment'])
        except:
            invstmtrq = None

        response = client.request_statements(
            user=config['ofxuser'],
            password=config['ofxpswd'],
            stmtrqs=[stmtrq],
            invstmtrqs=[invstmtrq]
        )

        fname = '{}_{}.ofx'.format(config['fid'], config['acctnum']) 
        with open(fname, 'w') as ofxfile:
            print(response.text, file=ofxfile)

        return fname
