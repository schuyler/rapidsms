#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8

"""
In order to use the Twilio backend, you must install the Python SDK from
http://github.com/twilio/twilio-python. You can install it via pip with:

    pip install twilio

Next, add the backend to the list of INSTALLED_BACKENDS in your settings.py:

    "twilio_account" : {"ENGINE":  "rapidsms.backends.twilio", 
                "host": "myserver.com",
                "port": 8189,
                "sid": "ACxxxxxxxxxxx",
                "token": "yyyyyyyyyyyyyy",
                "number": "+1415zzzzzzz"
        }

(Make sure that the number is in E.164 format as specified in the
Twilio API docs, as this will be used to validate incoming messages.)

Next, be sure to go into the Twilio dashboard and configure the SMS request URL
for your phone number (or your app) to *HTTP GET* from "http://{host}:{port}/"
as you configured it in your settings.py. Be sure to use HTTP GET and *not*
POST!

"""

from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.core.servers.basehttp import WSGIRequestHandler

from ..log.mixin import LoggerMixin
from .http import RapidHttpBackend, RapidWSGIHandler

from ..utils.modules import try_import
twilio_rest = try_import("twilio.rest")

class TwilioBackend(RapidHttpBackend):
    _title = "Twilio"

    def configure(self, host="0.0.0.0", port=8189, sid=None, token=None, number=None):
        if twilio_rest is None:
            raise ImportError(
                    "The rapidsms.backends.twilio engine is not available "
                    "because the Twilio Python SDK is not installed.")
        if not all((sid, token, number)):
            raise Exception("You must set the 'sid', 'token', and 'number' "
                            "config parameters for your Twilio account.")
        self.host = host
        self.port = port
        self.sid = sid
        self.number = number
        self.handler = RapidWSGIHandler()
        self.handler.backend = self
        self.client = twilio_rest.TwilioRestClient(sid, token)

    def handle_request(self, request):
        self.debug('Received request: %s' % request.GET)
        # for security check that the account SID matches
        account_sid = request.GET.get("AccountSid", "")
        to_number = request.GET.get("To", "")
        if account_sid != self.sid or to_number != self.number:
            return HttpResponseBadRequest("Missing ID.")
        sms = request.GET.get("Body", "")
        sender = request.GET.get("From", "")
        if not sms or not sender:
            return HttpResponseBadRequest("Missing fields.")
        now = datetime.utcnow()
        try:
            msg = self.message(sender, sms, now)
        except Exception, e:
            self.exception(e)
            raise        
        self.route(msg)
        return HttpResponse("")
    
    def send(self, message):
        self.info('Sending message: %s' % message)
        response = None
        try:
            response = self.client.sms.messages.create(
                    to=message.connection.identity,
                    from_=self.number,
                    body=message.text)
        except Exception, e:
            self.exception(e)
            return
        self.info('SENT')
        self.debug(response)
