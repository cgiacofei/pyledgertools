"""OFX downloader."""

from collections import defaultdict
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
        stmtrqs = defaultdict(list)
        try:
            acct = config.get('checking', config['savings'])
            stmtrqs['stmtrqs'].append(
                StmtRq(
                    acctid=acct,
                    dtstart=config['dtstart'],
                    dtend=config['dtend']
                )
            )
            fname = '{}_{}.ofx'.format(
                config['fid'],
                config.get('checking', config['savings'])
            )
        except:
            pass

        try:
            stmtrqs['invstmtrqs'].append(
                InvStmtRq(
                    acctid=config['investment'],
                    dtstart=config['dtstart'],
                    dtend=config['dtend']
                )
            )
            fname = '{}_{}.ofx'.format(
                config['fid'],
                config['investment']
            )
        except:
            pass

        user = config['ofxuser']
        pswd = config['ofxpswd']
        response = client.request_statements(user=user, password=pswd, **stmtrqs)

        with open(fname, 'w') as ofxfile:
            print(response.read(), file=ofxfile)

        return fname
