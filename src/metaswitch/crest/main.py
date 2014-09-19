#!/usr/bin/env python

# @file main.py
#
# Project Clearwater - IMS in the Cloud
# Copyright (C) 2013  Metaswitch Networks Ltd
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version, along with the "Special Exception" for use of
# the program along with SSL, set forth below. This program is distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details. You should have received a copy of the GNU General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.
#
# The author can be reached by email at clearwater@metaswitch.com or by
# post at Metaswitch Networks Ltd, 100 Church St, Enfield EN2 6BQ, UK
#
# Special Exception
# Metaswitch Networks Ltd  grants you permission to copy, modify,
# propagate, and distribute a work formed by combining OpenSSL with The
# Software, or a work derivative of such a combination, even if such
# copying, modification, propagation, or distribution would otherwise
# violate the terms of the GPL. You must comply with the GPL in all
# respects for all of the code used other than OpenSSL.
# "OpenSSL" means OpenSSL toolkit software distributed by the OpenSSL
# Project and licensed under the OpenSSL Licenses, or a work based on such
# software and licensed under the OpenSSL Licenses.
# "OpenSSL Licenses" means the OpenSSL License and Original SSLeay License
# under which the OpenSSL Project distributes the OpenSSL toolkit software,
# as those licenses appear in the file LICENSE-OPENSSL.

import metaswitch.crest
import os
import argparse
import logging
import syslog
from sys import executable
from socket import AF_INET

import cyclone.options
import cyclone.web
from twisted.internet import reactor

from metaswitch.crest import api
from metaswitch.crest import settings, logging_config
from metaswitch.common import utils
from metaswitch.crest import PDLog

_log = logging.getLogger("crest")

def shutdown_before():
    metaswitch.crest.PDLog.CREST_SHUTTING_DOWN.log()
    api.base.shutdownStats()

def create_application():
    app_settings = {
        "gzip": True,
        "cookie_secret": settings.COOKIE_SECRET,
        "debug": settings.CYCLONE_DEBUG,
    }
    application = cyclone.web.Application(api.get_routes(), **app_settings)

    # Initialize all modules
    api.initialize(application)
    return application

def standalone():
    """
    Initializes Tornado and our application.  Forks worker processes to handle
    requests.  Does not return until all child processes exit normally.
    """

    # Parse arguments
    parser = argparse.ArgumentParser(description="Homer web server")
    parser.add_argument("--background", action="store_true", help="Detach and run server in background")
    parser.add_argument("--worker-processes", default=1, type=int)
    parser.add_argument("--shared-http-fd", default=None, type=int)
    parser.add_argument("--process-id", default=0, type=int)
    args = parser.parse_args()

    # We don't initialize logging until we fork because we want each child to
    # have its own logging and it's awkward to reconfigure logging that is
    # defined by the parent.
    application = create_application()

    if args.background:
        # Get a new logfile, rotating the old one if present.
        err_log_name = os.path.join(settings.LOGS_DIR, settings.LOG_FILE_PREFIX + "-err.log")
        try:
            os.rename(err_log_name, err_log_name + ".old")
        except OSError:
            pass
        # Fork into background.
        utils.daemonize(err_log_name)

    # Drop a pidfile.
    pid = os.getpid()
    with open(settings.PID_FILE, "w") as pidfile:
        pidfile.write(str(pid) + "\n")

    utils.install_sigusr1_handler(settings.LOG_FILE_PREFIX)

    # Setup logging
    logging_config.configure_logging(args.process_id)
    logging_config.configure_syslog()

    metaswitch.crest.PDLog.CREST_STARTING.log()

    # setup accumulators and counters for statistics gathering
    api.base.setupStats(args.process_id, args.worker_processes)

    if args.shared_http_fd:
        reactor.adoptStreamPort(args.shared_http_fd, AF_INET, application)
    else:
        # Cyclone
        http_port = reactor.listenTCP(settings.HTTP_PORT, application, interface=settings.LOCAL_IP)
        _log.info("Listening for HTTP on port %s", settings.HTTP_PORT)
        metaswitch.crest.PDLog.CREST_UP.log()

        for process_id in range(1, args.worker_processes):
            reactor.spawnProcess(None, executable, [executable, __file__,
                                 "--shared-http-fd", str(http_port.fileno()),
                                 "--process-id", str(process_id)],
                                 childFDs={0: 0, 1: 1, 2: 2, http_port.fileno(): http_port.fileno()},
                                 env = os.environ)

    # We need to catch the shutdown request so that we can properly stop
    # the ZMQ interface; otherwise the reactor won't shutdown on a SIGTERM 
    # and will be SIGKILLed when the service is stopped.
    reactor.addSystemEventTrigger('before', 'shutdown', shutdown_before)

    # Kick off the reactor to start listening on configured ports
    reactor.run()

if __name__ == '__main__':
    standalone()
