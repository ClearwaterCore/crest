#!/usr/bin/python

# @file base.py
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


import sys
import unittest
import uuid
from cyclone.web import HTTPError
from twisted.python.failure import Failure
from metaswitch.crest.api import base
from monotonic import monotonic
from time import sleep

from mock import patch, MagicMock

class TestBaseHandler(unittest.TestCase):

    def setUp(self):
        super(TestBaseHandler, self).setUp()
        self.app = MagicMock()
        self.request = MagicMock()
        self.request.method = "GET"
        self.request.headers = {}
        self.handler = base.BaseHandler(self.app, self.request)

        # Mock out zmq so we don't fail if we try to report stats during the
        # test.
        self.real_zmq = base.zmq
        base.zmq = MagicMock()

    def tearDown(self):
        base.zmq = self.real_zmq
        del self.real_zmq

    def test_prepare(self):
        self.request.headers = {}
        self.handler.prepare()

    @patch('cyclone.web.RequestHandler')
    def test_write_msgpack(self, rh):
        self.handler.prepare()
        rh.write = MagicMock()
        self.request.headers["Accept"] = "application/x-msgpack"
        self.handler.write({"a": "b"})
        rh.write.assert_called_once_with(self.handler, '\x81\xa1a\xa1b')

    @patch('cyclone.web.RequestHandler')
    def test_write_json(self, rh):
        self.handler.prepare()
        rh.write = MagicMock()
        self.request.headers["Accept"] = "application/json"
        data = {"a": "b"}
        self.handler.write(data)
        rh.write.assert_called_once_with(self.handler, data)

    def test_bad_status_code_error(self):
        self.handler.send_error = MagicMock()
        e = HTTPError(799)
        f = Failure(e)
        self.handler._handle_request_exception(f)
        self.handler.send_error.assert_called_once_with(500, exception=e)

    def test_uncaught_exception(self):
        self.handler.send_error = MagicMock()
        e = Failure(Exception("uncaught"))
        self.handler._handle_request_exception(e)
        self.handler.send_error.assert_called_once_with(500, exception=e)

    def test_send_error_redirect(self):
        self.handler.get_argument = MagicMock(return_value="/foo/")
        self.handler.redirect = MagicMock()
        self.handler.send_error(400, {"foo": "bar"})
        self.handler.redirect.assert_called_once_with(
            '/foo/?detail=%7B%7D&error=true&message=Bad%20Request&'
            'reason=%7B%27foo%27%3A%20%27bar%27%7D&status=400')

    def test_write_error_debug(self):
        self.app.settings.get = MagicMock(return_value=True)
        self.handler.finish = MagicMock()
        try:
            raise Exception()
        except Exception:
            exc_info = sys.exc_info()
            self.handler.write_error(500, exc_info=exc_info)
        data = self.handler.finish.call_args[0][0]
        self.assertTrue("exception" in data)
        self.assertTrue("Traceback" in "".join(data['exception']), data["exception"])

    def test_write_error_no_debug_204(self):
        self.app.settings.get = MagicMock(return_value=True)
        self.handler.finish = MagicMock()
        try:
            raise Exception()
        except Exception:
            exc_info = sys.exc_info()
            self.handler.write_error(204, exc_info=exc_info)
        data = self.handler.finish.call_args[0][0]
        self.assertIsNone(data)

    def test_check_request_age_decorator(self):
        """ Test the check_request_age decorator with a recent request"""
        # Set the start time of the request to now
        self._start = monotonic()
        # Call a mock function with the decorator - as the request is recent, the
        # underlying function should be called as normal
        decorator = self.handler.check_request_age
        func = MagicMock()
        decorated = decorator(func)
        decorated(self, "arg1")
        func.assert_called_once_with(self, "arg1")

    def test_check_request_age_decorator_error(self):
        """ Test the check_request_age decorator with an old request"""
        self.send_error = MagicMock()
        # Ensure that the request is too old
        self._start = monotonic() - 1000
        # Call a mock function with the decorator - as the request is old, the decorator
        # should send a 503 error and the underlying function should not be called.
        decorator = self.handler.check_request_age
        func = MagicMock()
        decorated = decorator(func)
        decorated(self, "arg")
        self.send_error.assert_called_once_with(503, "Request too old")
        self.assertFalse(func.called)

SIP_URI = "sip:1234567890@cw-ngv.com"
OWNER_ID = uuid.uuid4()

class TestUnknownApiHandler(unittest.TestCase):

    def setUp(self):
        super(TestUnknownApiHandler, self).setUp()
        self.app = MagicMock()
        self.request = MagicMock()
        self.handler = base.UnknownApiHandler(self.app, self.request)

    def test_get(self):
        self.handler.send_error = MagicMock()
        self.handler.get()
        self.handler.send_error.assert_called_once_with(404, "Request for unknown API")

class TestLoadMonitor(unittest.TestCase):

    def test_divide_by_zero(self):
        """
        Test that twice the LoadMonitor's REQUESTS_BEFORE_ADJUSTMENT requests all
        arriving at once don't cause a ZeroDivisionError when they all
        complete.
        """

        # Create a LoadMonitor with a bucket size twice as big as the
        # REQUESTS_BEFORE_ADJUSTMENT so we can add all the requests at once
        size = base.LoadMonitor.REQUESTS_BEFORE_ADJUSTMENT * 2
        load_monitor = base.LoadMonitor(0.1, size, size, size)

        success = True

        # Add all the requests at once
        for _ in range(size):
            success &= load_monitor.admit_request()

        # All the requests should have been admitted
        self.assertTrue(success)

        # Now, let the requests finish
        try:
            for _ in range(size):
                load_monitor.request_complete()
                load_monitor.update_latency(0.1)
        except ZeroDivisionError:
            success = False

        self.assertTrue(success)

    def test_rate_increase(self):
        """
        Test that when we have accepted more than half the maximum permitted requests
        in the last update period, we increase the permitted request rate.
        """

        # Create a load monitor as we do in the main crest base
        load_monitor = base.LoadMonitor(0.1, 100, 100, 10)

        success = True 
        initial_rate = load_monitor.bucket.rate
        # We need this to be a float, so that the sleeps below don't round to 0
        update_period = float(load_monitor.SECONDS_BEFORE_ADJUSTMENT)

        # The number of requests we need to send to go over the threshold is: 
        threshold_requests = load_monitor.bucket.rate * load_monitor.SECONDS_BEFORE_ADJUSTMENT

        # To simulate the right load, we will add three sets of half this threshold the time period
        # and then trigger the update_latency function at the end of it.
        for _ in range(3):
            for _ in range(threshold_requests/2):
                load_monitor.admit_request()
                load_monitor.request_complete()
                load_monitor.update_latency(0.08)
            sleep(update_period/4)

        # Do one last sleep, so that we pass the time threshold
        sleep(update_period/4 + 0.5)

        # Do one more request, and then test to see if the rate has increased
        load_monitor.admit_request()
        load_monitor.request_complete()
        load_monitor.update_latency(0.08)

        final_rate = load_monitor.bucket.rate
        print("Initial rate {}, final rate {}".format(initial_rate, final_rate))
        self.assertTrue(final_rate > initial_rate)

        # Test if errors > threshold, rate reduced
        # same, but hss overload

        # Test if accepted > min_thresh, and t > 2, rate increased
        # Test if accepted > min thresh and t < 2, no change
        # Test if accepted < min thresh and t > 2, no change

if __name__ == "__main__":
    unittest.main()
