# @file logging_config.py
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
import logging
import logging.handlers
import syslog
import PDLog
import time

from metaswitch.crest import settings
from metaswitch.crest.PDLog import PDLog

import twisted.python

class TwistedLogObserver(twisted.python.log.FileLogObserver):
    """
    A log observer for catching errors logged in the twisted package
    so that we can send them to syslog.
    """
    def __init__(self):
        self.logLevel = logging.ERROR

    def emit(self,eventDict):
        """Custom emit for FileLogObserver"""

        from metaswitch.crest import PDLog
        from metaswitch.crest.PDLog import TWISTED_ERROR

        text = twisted.python.log.textFromEventDict(eventDict)
        if text is None:
            return
        if eventDict['isError']:
            level = logging.ERROR
        elif 'level' in eventDict:
            level = eventDict['level']
        else:
            level = settings.LOG_LEVEL
        if level >= self.logLevel:
            fmtDict = {'text': text.replace("\n", "\n\t")}
            msgStr = twisted.python.log._safeFormat("twisted %(text)s\n", fmtDict)
            PDLog.TWISTED_ERROR.log(msgStr)

logger=TwistedLogObserver()
twisted.python.log.addObserver(logger.emit)

def configure_syslog():
    syslog.openlog(settings.LOG_FILE_PREFIX, logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL6)
