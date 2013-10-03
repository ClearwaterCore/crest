# @file handlers.py
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

import logging
import time

from twisted.internet import defer
from .db import IMPI, IMPU

_log = logging.getLogger("crest.api.homestead.cache")


class Cache(object):

    @staticmethod
    def generate_timestamp():
        """
        Return a timestamp (in ms) suitable for supplying to cache updates.

        Cache update operation can happen in parallel and involve writes to
        multiple rows. This could leave the cache inconsistent (if some of the
        database ended upwith some rows from update A and other from update B).

        To alleviate this the cache user must use the same timestamp for _all_
        related updates. This ensures the database ends up with all the rows
        from either update A or update B (though we can't tell which), meaning
        the cache is consistent, even if it isn't completely up-to-date.
        """
        return time.time() * 1000000

    @defer.inlineCallbacks
    def get_digest(self, private_id, public_id=None):
        digest_ha1 = yield IMPI(private_id).get_digest_ha1(public_id)
        _log.debug("Fetched digest for private ID '%s' from cache: %s" %
                   (private_id, digest_ha1))
        defer.returnValue(digest_ha1)

    @defer.inlineCallbacks
    def get_ims_subscription(self, public_id, private_id=None):
        xml = yield IMPU(public_id).get_ims_subscription()
        _log.debug("Fetched XML for public ID '%s' from cache:\n%s" %
                   (public_id, xml))
        defer.returnValue(xml)

    @defer.inlineCallbacks
    def put_digest(self, private_id, digest, timestamp):
        _log.debug("Put private ID '%s' into cache with digest: %s" %
                   (private_id, digest))
        yield IMPI(private_id).put_digest_ha1(digest, timestamp)

    @defer.inlineCallbacks
    def put_associated_public_id(self, private_id, public_id, timestamp):
        _log.debug("Associate public ID '%s' with private ID '%s' in cache" %
                   (public_id, private_id))
        yield IMPI(private_id).put_associated_public_id(public_id, timestamp)

    @defer.inlineCallbacks
    def put_ims_subscription(self, public_id, xml, timestamp):
        _log.debug("Put public ID '%s' into cache with XML:\n%s" %
                   (public_id, xml))
        yield IMPU(public_id).put_ims_subscription(xml, timestamp)

    @defer.inlineCallbacks
    def delete_private_id(self, private_id, timestamp):
        _log.debug("Delete private ID '%s' from cache" % private_id)
        yield IMPI(private_id).delete_row(timestamp)

    @defer.inlineCallbacks
    def delete_public_id(self, public_id, timestamp):
        _log.debug("Delete public ID '%s' from cache" % public_id)
        yield IMPU(public_id).delete_row(timestamp)
