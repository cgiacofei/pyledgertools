"""Define custom plugin classes."""

from yapsy.IPlugin import IPlugin


class IDownload(IPlugin):
    pass


class IClassify(IPlugin):
    pass


class IModify(IPlugin):
    pass
