from rapidsms.apps.base import AppBase
from rapidsms.models import Connection, Backend
from rapidsms.messages.outgoing import OutgoingMessage
from rapidsms.messages.incoming import IncomingMessage
from settings import GATEWAY as config
from urllib import urlopen, quote_plus

"""
This app depends on the rapidsms.contrib.ajax app to run.

Add something like this to your settings.py:

GATEWAY = {
    "backend": "backend_name",
    "secret": "something secret",
    "push": "http://your.app/endpoint?from=%(from)s&txt=%(txt)s&secret=%(secret)s"
}

"""

class App(AppBase):
    def ajax_GET_send(self, params):
        if params.get("secret",[None])[0] != config["secret"]:
            return {'error': 'authentication failure'}
        target = params.get("to", [None])[0]
        text = params.get("txt", [None])[0]
        if not target or not text:
            return {'error': '`to` or `txt` parameter missing'}
        backend = Backend.objects.get(name=config["backend"])
        connection = Connection(backend=backend, identity=target)
        # OutgoingMessage does string template formatting by
        # default, so forestall it
        text = text.replace("%","%%") 
        message = OutgoingMessage(connection, text)
        result = self.router.outgoing(message)
        if result:
            return {'success': result}
        else:
            return {'error': result}

    def default(self, msg):
        url = config["push"] % {
            "from": quote_plus(msg.connection.identity),
            "txt": quote_plus(msg.text),
            "secret": config["secret"]
        }
        print "GETTING %s" % url
        urlopen(url).read()
        return True
