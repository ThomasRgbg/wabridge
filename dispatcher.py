#!/usr/bin/python3
# -*- coding: utf-8 -*-

import zmq
import logging
import datetime
import sys

from zmqhandler import ZMQSender
from dispatcher_config import usermap


class MsgDispatcher(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.zmq = ZMQSender()
        filename = '/var/log/xmppuser/messages.txt'
        if sys.version_info < (3, 0):
            self.msglogfile = open(filename, 'at', 1)
        else:
            self.msglogfile = open(filename, 'at', 1, encoding='latin-1')

    def msglog(self, text):
        now = datetime.datetime.now()
        formattedDate = now.strftime('[%d.%m.%Y %H:%M]:')
        self.msglogfile.write( formattedDate + text.encode('utf-8').decode('latin1','replace') + '\n' )
        self.msglogfile.flush()

    def translate(self, source, sourceside):
        self.logger.debug('translate: source: {0}, sourceside {1}'.format(source,sourceside) )

        if sourceside == 'xmpp':
            if source in usermap.keys():
                self.logger.debug('translate: xmpp {0} into wa {1}'.format(source,usermap[source]) )
                return usermap[source]
            else:
                self.logger.error("translate: Unknown Whatsup ID for {0}".format(source))
                return None
        elif sourceside == 'whats':
            if source in usermap.values():
                dest = ([xmppname for xmppname, whatsname in usermap.items() if whatsname == source])
                self.logger.debug('translate: wa {0} into xmpp {1}'.format(source,dest) )
                return dest
            else:
                self.logger.error("translate: Unknown XMPP ID for {0}".format(source))
                return None
        else:
            return None
                  
    def send2xmpp(self, fromwhats, towhats, text, extra_data=None):
        self.msglog(fromwhats + '->' + towhats + ': ' + text + '|' + str(extra_data) )
        fromxmpp = self.translate(fromwhats, 'whats')
        toxmpp = self.translate(towhats, 'whats')

        if text == None or text == 'None':
            self.logger.error("send2xmpp: Empty text for {0} -> {1}".format(fromwhats, towhats))

        elif (fromxmpp == None) and (toxmpp == None) and (fromwhats == 'wa_control'):
            self.zmq.send_message(source='whats_unknown@felsenkuschler.de', dest=towhats, text=text, extra_data=extra_data)

        # Unkown sender, but receiver is known
        elif (fromxmpp == None) and (toxmpp != None):
            for dest in toxmpp:
                #text2 = '[ +' + fromwhats.split('@')[0] + ' | +' + towhats.split('@')[0] + ' ]  ' + text
                text2 = text
                # self.zmq.send_message(source='whats_unknown@felsenkuschler.de', dest=dest, text=text2, extra_data=extra_data)
                self.zmq.send_message(source='wa_component', dest=dest, text=text2, extra_data=fromwhats)

        # Sender know, receiver known
        elif (fromxmpp != None) and (toxmpp != None):
            if fromxmpp[0].startswith('whats_schabel'):
                self.zmq.send_message(source=fromxmpp[0], dest='schabelecho@felsenkuschler.de', text=text, extra_data=extra_data)
            else: 
                for source in fromxmpp:
                    for dest in toxmpp:
                        self.zmq.send_message(source=source, dest=dest, text=text, extra_data=extra_data)

        # Else (should not be hit)
        else:
            self.logger.error("send2xmpp: Could not dispatch:  [{0} -> {1}] {2}".format(fromwhats, towhats, text))
            self.zmq.send_message(source='whats_unknown@felsenkuschler.de', dest='schabelecho@felsenkuschler.de', text='[dispatcher error]'+text, extra_data=extra_data)



    def send2whats(self, fromxmpp, toxmpp, text, extra_data=None):
        self.msglog(fromxmpp + '->' + toxmpp + ': ' + text+ '|' + str(extra_data))
        self.logger.debug('send2whats: ' + fromxmpp + '->' + toxmpp + ': ' + text + '|' + str(extra_data))
        fromwhats = self.translate(fromxmpp, 'xmpp')
        toxwhats = self.translate(toxmpp, 'xmpp')
        if text == None or text == 'None':
            self.logger.error("send2whats: Empty text for {0} -> {1}".format(fromxmpp, toxmpp))
        elif (fromwhats != None) and (toxmpp.startswith('whats_unknown') ):
            self.zmq.send_message(source=fromwhats, dest=fromwhats, text=text, extra_data=extra_data)
        elif (fromwhats != None) and (toxwhats != None):
            self.zmq.send_message(source=fromwhats, dest=toxwhats, text=text, extra_data=extra_data)
        else:
            self.logger.error("send2whats: Could not dispatch:  [{0} -> {1}] {2}".format(fromxmpp, toxmpp, text))


# simple test programm
if __name__ == '__main__':
    disp = MsgDispatcher()

    xmpp = 'test@jabber.org'
    print(xmpp + ' = ' + disp.translate(xmpp, 'xmpp'))

    whats = '123456'
    print(whats + ' = ' +  disp.translate(whats, 'whats'))

    disp.send2xmpp('49123456', '4956789', 'Test', None)

