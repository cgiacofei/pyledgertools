#!/usr/bin/env python
""" Base class for daemonizing stuff.
See here:
http://code.activestate.com/recipes/66012-fork-a-daemon-process-on-unix
"""

import atexit
import logging
import logging.config
import os
from signal import SIGTERM
import sys
import time
import yaml


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """
    def __init__(self, pidfile, config):
        self.pidfile = pidfile

        with open(config, 'r') as c_file:
            c_yaml = yaml.load(c_file)
            log_config = c_yaml['global']['logging']

        logging.config.dictConfig(log_config.get('logging', None))
        self.logger = logging.getLogger(__name__)

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            self.logger.error(
                'fork #1 failed: {} ({})'.format(e.errno, e.strerror)
            )
            sys.exit(1)

            # decouple from parent environment
            os.chdir('/')
            os.setsid()
            os.umask(0)

            # do second fork
            try:
                pid = os.fork()
                if pid > 0:
                    # exit from second parent
                    sys.exit(0)
            except OSError as e:
                self.logger.error(
                    'fork #2 failed: {} ({})'.format(e.errno, e.strerror)
                )
                sys.exit(1)

            # write pidfile
            atexit.register(self.delpid)
            self.pid = str(os.getpid())

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        if self.pid:
            self.logger.info('pidfile already exist. Daemon already running?')
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """

        if not self.pid:
            self.logger.info('pidfile does not exist. Daemon not running?')
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(self.pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                else:
                    print(str(err))
                    sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """Override this method when you subclass Daemon. It will be called
        after the process has been daemonized by start() or restart().
        """
        raise NotImplementedError('Need to overide run method.')

    @property
    def pid(self):
        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        return pid

    @pid.setter
    def pid(self, id):
        with open(self.pidfile, 'w+') as pf:
            pf.write('{}\n'.format(id))
