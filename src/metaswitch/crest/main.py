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


import os
import argparse
import logging
from sys import executable
from socket import AF_INET

import cyclone.options
import cyclone.web
import twisted.internet.address
from twisted.internet import reactor

from metaswitch.crest import api
from metaswitch.crest import settings, logging_config
from metaswitch.common import utils

_log = logging.getLogger("crest")

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
    # Hack to work-around issue with Cyclone and UNIX domain sockets
    twisted.internet.address.UNIXAddress.host = "localhost"

    # Parse arguments
    parser = argparse.ArgumentParser(description="Homer web server")
    parser.add_argument("--background", action="store_true", help="Detach and run server in background")
    parser.add_argument("--signaling-namespace", action="store_true", help="Server running in signaling namespace")
    parser.add_argument("--worker-processes", default=1, type=int)
    parser.add_argument("--shared-http-tcp-fd", default=None, type=int)
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

    # setup accumulators and counters for statistics gathering
    api.base.setupStats(args.process_id, args.worker_processes)

    # Initialize reactor ports and create worker sub-processes
    if args.process_id == 0:
        # Main process startup, create UNIX domain socket for nginx front-end (used for
        # normal operation and as a bridge from the default namespace to the signaling
        # namespace in a multiple interface configuration).
        unix_sock_name = settings.HTTP_UNIX + "-0"
        _log.info("Going to listen for HTTP on UNIX socket %s", unix_sock_name)
        reactor.listenUNIX(unix_sock_name, application)

        if args.signaling_namespace and settings.PROCESS_NAME == "homer":
            # Running in signaling namespace as Homer, create TCP socket for XDMS requests
            # from signaling interface
            _log.info("Going to listen for HTTP on TCP port %s", settings.HTTP_PORT)
            http_tcp_port = reactor.listenTCP(settings.HTTP_PORT, application, interface=settings.LOCAL_IP)

            # Spin up worker sub-processes, passing TCP file descriptor
            for process_id in range(1, args.worker_processes):
                reactor.spawnProcess(None, executable, [executable, __file__,
                                     "--shared-http-tcp-fd", str(http_tcp_port.fileno()),
                                     "--process-id", str(process_id)],
                                     childFDs={0: 0, 1: 1, 2: 2, http_tcp_port.fileno(): http_tcp_port.fileno()},
                                     env = os.environ)
        else:
            # Spin up worker sub-processes
            for process_id in range(1, args.worker_processes):
                reactor.spawnProcess(None, executable, [executable, __file__,
                                     "--process-id", str(process_id)],
                                     childFDs={0: 0, 1: 1, 2: 2},
                                     env = os.environ)
    else:
        # Sub-process startup, create UNIX domain socket for nginx front-end based on
        # process ID. 
        unix_sock_name = settings.HTTP_UNIX + "-" + str(args.process_id)
        _log.info("Going to listen for HTTP on UNIX socket %s", unix_sock_name)
        reactor.listenUNIX(unix_sock_name, application)

        # Create TCP socket if file descriptor was passed.
        if args.shared_http_tcp_fd:
            reactor.adoptStreamPort(args.shared_http_tcp_fd, AF_INET, application)

    # Kick off the reactor to start listening on configured ports
    reactor.run()

if __name__ == '__main__':
    standalone()
