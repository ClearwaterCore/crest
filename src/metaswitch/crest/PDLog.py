# @file PDLog.py
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

import syslog, settings, weakref
from api import monotime
from api.monotime import monotonic_time
from metaswitch.crest import settings

class PDLog:
    """
    Base class for Enhanced Node Troubleshooting (ENT) logs. Provides
    storage for the log definition plus the mechanism for logging
    to syslog.
    """

    _instances = set()
    
    def __init__(self, name, level, code, msg, cause, effect, action):
        self.level = level
        self.code = code
        self.msg = msg
        self.name = name
        self.cause = cause
        self.effect = effect
        self.action = action
        self.last_emit = 0
        self._instances.add(weakref.ref(self))

    def __str__(self):
        return self.name

    def getKey(self):
        return self.code

    @classmethod
    def getinstances(cls):
        dead = set()
        for ref in cls._instances:
            obj = ref()
            if obj is not None:
                yield obj
            else:
                dead.add(ref)
        cls._instances -= dead

    def log(self):
        since_last_emit = monotonic_time() - self.last_emit
        if since_last_emit > settings.PDLOG_RATE_LIMIT:
            syslog.syslog(self.level, ("%d (%s) " + self.msg) % (self.code, self.name))
            self.last_emit = monotonic_time()

    @classmethod
    def printDefs(cls):
        level2text={ syslog.LOG_INFO : 'INFO', syslog.LOG_WARNING : 'WARNING', syslog.LOG_ERR : 'ERROR', syslog.LOG_CRIT : 'CRITICAL' }
        for obj in sorted(cls.getinstances(), key=cls.getKey):
            print obj.name
            print "   level: %s" % level2text[obj.level]
            print "   code: %s" % obj.code
            print "   msg: '%s'" % obj.msg
            print "   cause: '%s'" % obj.cause
            print "   effect: '%s'" % obj.effect
            print "   action: '%s'" % obj.action

class PDLog1(PDLog):
    def log(self, v1):
        syslog.syslog(self.level, ("%d (%s) " + self.msg) % (self.code, self.name, v1))

class PDLog2(PDLog):
    def log(self, v1, v2):
        syslog.syslog(self.level, ("%d (%s) " + self.msg) % (self.code, self.name, v1, v2))

class PDLog3(PDLog):
    def log(self, v1, v2, v3):
        syslog.syslog(self.level, ("%d (%s) " + self.msg) % (self.code, self.name, v1, v2, v3))

class PDLog4(PDLog):
    def log(self, v1, v2, v3, v4):
        syslog.syslog(self.level, ("%d (%s) " + self.msg) % (self.code, self.name, v1, v2, v3, v4))

CREST_SHUTTING_DOWN = PDLog("CREST_SHUTTING_DOWN",
    syslog.LOG_INFO, 1,
    "Service '%s' is shutting down" % settings.LOG_FILE_PREFIX,
    "A 'shutdown' was requested by an external entity",
    "%s service is no longer available" % settings.LOG_FILE_PREFIX,
    "Verify that the shutdown request was authorized"
    )

CREST_STARTING = PDLog("CREST_STARTING",
    syslog.LOG_INFO, 2,
    "Service '%s' is starting" % settings.LOG_FILE_PREFIX,
    "A 'start' was requested by an external entity",
    "%s service is starting" % settings.LOG_FILE_PREFIX,
    ""
    )

CREST_UP = PDLog("CREST_UP",
    syslog.LOG_INFO, 3,
    "Service '%s' is up and listening for HTTP on port %s" % (settings.LOG_FILE_PREFIX, settings.HTTP_PORT),
    "A shutdown was requested by an external entity",
    "%s service is available" % settings.LOG_FILE_PREFIX,
    ""
    )

API_UNKNOWN = PDLog1("API_UNKNOWN",
    syslog.LOG_INFO, 4,
    "Request for unknown API - %s",
    "A client made a request using an unknown API",
    "A 404 error is returned to the client",
    ""
    )

API_GUESSED_JSON = PDLog1("API_GUESSED_JSON",
    syslog.LOG_WARNING, 5,
    "Guessed MIME type of uploaded data as JSON from client %s",
    "A client sent data of unspecified type, so it was assumed to be JSON",
    "JSON mime type is assumed",
    "The client should be fixed so as to specify a MIME type"
    )

API_GUESSED_URLENCODED = PDLog1("API_GUESSED_URLENCODED",
    syslog.LOG_WARNING, 6,
    "Guessed MIME type of uploaded data as URL encoded from client %s",
    "A client sent data of unspecified type, so it was assumed to be URL encoded",
    "URL encoding is assumed",
    "The client should be fixed so as to specify a MIME type for the data"
    )

API_OVERLOADED = PDLog("API_OVERLOADED",
    syslog.LOG_INFO, 7,
    "Service '%s' has become overloaded and rejecting requests" % settings.LOG_FILE_PREFIX,
    "The service has received too many requests and has become overloaded",
    "Requests are being rejected",
    "Determine the cause of the overload and scale appropriately"
    )

API_NOTOVERLOADED = PDLog("API_NOTOVERLOADED",
    syslog.LOG_INFO, 8,
    "Service '%s' is no longer overloaded and is accepting requests" % settings.LOG_FILE_PREFIX,
    "The service is no longer overloaded",
    "Requests are being accepted",
    ""
    )

API_HTTPERROR = PDLog1("API_HTTPERROR",
    syslog.LOG_WARNING, 9,
    "HTTP error: %s",
    "The service has received too many requests and has become overloaded",
    "The request has been rejected",
    ""
    )

API_UNCAUGHT_EXCEPTION = PDLog1("API_UNCAUGHT_EXCEPTION",
    syslog.LOG_ERR, 10,
    "Uncaught exception: %s",
    "An unexpected exception has occurred while processing a request",
    "The request has been rejected",
    "Gather diagnostics and report to customer service"
    )

TWISTED_ERROR = PDLog1("TWISTED_ERROR",
    syslog.LOG_ERR, 11,
    "Internal 'twisted' error: %s",
    "An unexpected internal error has occurred within the 'Twisted' component",
    "Unknown",
    "Gather diagnostics and report to customer service"
    )

