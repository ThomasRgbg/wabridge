#!/usr/bin/python
# -*- coding: utf-8 -*-

import zmq
import logging
import datetime

from zmqhandler import ZMQSender
from dispatcher_config import usermap


class MsgDispatcher(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.zmq = ZMQSender()
        filename = 'messages.txt'
        self.msglogfile = open(filename, 'ab', 0)

    def msglog(self, string):
        now = datetime.datetime.now()
        formattedDate = now.strftime(u'[%d.%m.%Y %H:%M]:')
        self.msglogfile.write( formattedDate + string.encode('utf-8') + '\n' )
        self.msglogfile.flush()

    def translate(self, source, sourceside):
        self.logger.debug(u'translate: source: {0}, sourceside {1}'.format(source,sourceside) )

        if sourceside == 'xmpp':
            if source in usermap.keys():
                self.logger.debug(u'translate: xmpp {0} into wa {1}'.format(source,usermap[source]) )
                return usermap[source]
            else:
                self.logger.error(u"translate: Unknown Whatsup ID for %s" % source)
                return None
        elif sourceside == 'whats':
            if source in usermap.values():
                dest = ([xmppname for xmppname, whatsname in usermap.items() if whatsname == source])[0]
                self.logger.debug(u'translate: wa {0} into xmpp {1}'.format(source,dest) )
                return dest
            else:
                self.logger.error(u"translate: Unknown XMPP ID for %s" % source)
                return None
        else:
            return None
                  
    def send2xmpp(self, fromwhats, towhats, text):
        self.msglog(fromwhats + '->' + towhats + ': ' + text)
        fromxmpp = self.translate(fromwhats, 'whats')
        toxmpp = self.translate(towhats, 'whats')

        if text == None or text == 'None':
            self.logger.error(u"send2xmpp: Empty text for %s -> %s" % (fromwhats, towhats))

        # Unkown sender, but receiver is known
        if (fromxmpp == None) and (toxmpp != None):
            self.zmq.send_message(source='whats_unknown@xxxx.de', dest=toxmpp, text='[' + fromwhats + '|' + towhats + ']' + text)

        # Sender know, receiver known
        elif (fromxmpp != None) and (toxmpp != None):
            if fromxmpp.startswith('whats_chatroom1'):
                self.zmq.send_message(source=fromxmpp, dest='echobot1@xxxx.de', text=text)
            else: 
                self.zmq.send_message(source=fromxmpp, dest=toxmpp, text=text)

        # Else (should not be hit)
        else:
            self.logger.error(u"send2xmpp: Could not dispatch:  [%s -> %s] %s" % (fromwhats, towhats, text))

    def send2whats(self, fromxmpp, toxmpp, text):
        self.msglog(fromxmpp + '->' + toxmpp + ': ' + text)
        self.logger.debug('send2whats: ' + fromxmpp + '->' + toxmpp + ': ' + text)
        fromwhats = self.translate(fromxmpp, 'xmpp')
        toxwhats = self.translate(toxmpp, 'xmpp')
        if text == None or text == 'None':
            self.logger.error(u"send2whats: Empty text for %s -> %s" % (fromxmpp, toxmpp))
        elif (fromwhats != None) and (toxwhats != None):
            self.zmq.send_message(source=fromwhats, dest=toxwhats, text=text)
        else:
            self.logger.error(u"send2whats: Could not dispatch:  [%s -> %s] %s" % (fromxmpp, toxmpp, text))


# simple test programm
if __name__ == '__main__':
    disp = MsgDispatcher()

    xmpp = 'test@jabber.org'
    print xmpp + ' = ' + disp.translate(xmpp, 'xmpp')

    whats = '123456'
    print whats + ' = ' +  disp.translate(whats, 'whats')

    disp.send2xmpp('49123456', '4956789', 'Test')

