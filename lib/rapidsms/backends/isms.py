from .base import BackendBase
from xml.etree import ElementTree
from urllib import urlopen, quote, unquote
from datetime import datetime
import time

"""
Driver for MultiTech Systems 'MultiModem iSMS' GSM modem.

Add to INSTALLED_BACKENDS:

    "isms_modem": {
        "ENGINE": "rapidsms.backends.isms",
        "host": "192.168.2.1",
        "port": 81,
        "user": "username",
        "passwd": "passwd",
        "interval": 1.0     # polling time in seconds
    }

"""

"""
<!-- example response from /recvmsg -->
<?xml version="1.0" encoding="ISO-8859-1" ?><Response><Response_End>1</Response_End>
<Unread_Available>1</Unread_Available>
<Msg_Count>01</Msg_Count>
<MessageNotification>
<Message_Index>1</Message_Index>
<ModemNumber>1:</ModemNumber>
<SenderNumber>+134784xxxxx</SenderNumber>
<Date>11/11/04</Date>
<Time>11:00:58</Time>
<EncodingFlag>ASCII</EncodingFlag>
<Message>Hello!</Message>
</MessageNotification>
</Response>
"""

def dumb_urlencode(seq):
    # can't use urlencode, b/c it uses quote_plus, and the iSMS modem doesn't change pluses to spaces
    return "&".join(quote(k)+"="+quote(v) for k, v in seq)

class IsmsBackend(BackendBase):
    def configure(self, host="192.168.2.1", port=81, user="admin", passwd="admin", interval=1.0):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.interval = interval

    def run(self):
        while self.running:
            time.sleep(self.interval)
            self.poll_modem()

    def poll_modem(self):
        context = ( # the iSMS modem actually cares about the parameter sequence :-o
            ("user", self.user),
            ("passwd", self.passwd)
        )
        url = "http://%s:%d/recvmsg?%s" % (self.host, self.port, dumb_urlencode(context))
        data = None
        try:
            xml = urlopen(url).read()
            data = ElementTree.fromstring(xml)
        except Exception, e:
            self.exception(e)
            return
        for note in data.findall("MessageNotification"):
            text = note.findtext("Message")
            sender = note.findtext("SenderNumber")
            if not text or not sender: continue
            try:
                msg = self.message(sender, unquote(text), datetime.utcnow())
                self.route(msg)
            except Exception, e:
                self.exception(e)
                continue

    def send(self, message):
        self.info('Sending message: %s' % message)
        context = (
            ('user', self.user),
            ('passwd', self.passwd),
            ('cat', '1'),
            ('to', message.connection.identity),
            ('text', message.text)
        )
        url = "http://%s:%d/sendmsg?%s" % (self.host, self.port, dumb_urlencode(context))
        try:
            self.debug('Sending: %s' % url)
            response = urlopen(url)
        except Exception, e:
            self.exception(e)
            return
        self.info('SENT')
        self.debug(response.read())
