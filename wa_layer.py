#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
based on yowsup-cli from https://github.com/tgalal/yowsup

Permission is hereby granted, free of charge, to any person obtaining a copy of this 
software and associated documentation files (the "Software"), to deal in the Software 
without restriction, including without limitation the rights to use, copy, modify, 
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to 
permit persons to whom the Software is furnished to do so, subject to the following 
conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR 
A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import sys
reload(sys)
sys.setdefaultencoding("UTF-8")

import argparse, sys, datetime
import time, base64, string, os
import logging
from dispatcher import MsgDispatcher


from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities      import OutgoingAckProtocolEntity
from yowsup.layers.protocol_iq.protocolentities        import PingIqProtocolEntity, ResultIqProtocolEntity
from yowsup.layers.auth                                import YowAuthenticationProtocolLayer
from yowsup.layers.network                             import YowNetworkLayer
from yowsup.layers                                     import YowLayerEvent 

from yowsup.common import YowConstants

logger = logging.getLogger(__name__)

class ChatLayer(YowInterfaceLayer):
    PROP_SEND_MSG_DETAILS  = "org.openwhatsapp.yowsup.prop.chat.sendmsg"
    EVENT_SEND_MESSAGE     = "org.openwhatsapp.yowsup.event.chat.sendmsg"
    EVENT_PING             = "org.openwhatsapp.yowsup.event.ping"
    EVENT_TERMINATE        = "org.openwhatsapp.yowsup.event.terminate"

    def __init__(self):
        super(ChatLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.dispatcher = MsgDispatcher()
        self.pingcount = 0
        self.terminate = False

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        messageType = messageProtocolEntity.getType()
        # print("onMessage: Got Type: %s" % messageType)
        if  messageType == "text":
            self.onTextMessage(messageProtocolEntity)
        elif messageType == "media":
            self.onMediaMessage(messageProtocolEntity)
        else:
            logger.error("onMessage: Unknown Type: %s " % messageType)

        #send receipt otherwise we keep receiving the same message over and over
        if True:
            receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom())
            self.toLower(receipt)

    def onTextMessage(self, message):
        wa_sender = message.getFrom(full = True)
        wa_rcvr =  self.getProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS)[0] + '@s.whatsapp.net' # TODO: Better way to get ? 
        author = message.getNotify() # Strange name, but seems to be correct
        text = message.getBody()
        formattedDate = datetime.datetime.fromtimestamp(message.getTimestamp()).strftime('[%d.%m. %H:%M]')

        logger.info('{0}[{1}/{2}]({3}) {4}'.format(formattedDate, wa_sender, wa_rcvr, author, text) )

        if message.isGroupMessage():
            text = formattedDate + ' ' + author + ': ' + text

        self.dispatcher.send2xmpp(wa_sender, wa_rcvr, text)

    def onMediaMessage(self, message):
        wa_sender = message.getFrom(full = True)
        wa_rcvr =  self.getProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS)[0] + '@s.whatsapp.net' # TODO: Better way to get ? 
        author = message.getNotify()  # Strange name, but seems to be correct
        url =  message.getMediaUrl()
        formattedDate = datetime.datetime.fromtimestamp(message.getTimestamp()).strftime('[%d.%m. %H:%M]')

        logger.info('{0}[{1}/{2}]({3}) {4}'.format(formattedDate, wa_sender, wa_rcvr, author, url) )

        if message.isGroupMessage():
            text = formattedDate + ' ' + author + ': ' + url
        else:
            text = url

        self.dispatcher.send2xmpp(wa_sender, wa_rcvr, text)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", "delivery")
        logger.debug('onReceipt: send ack')
        self.toLower(ack)

    def onEvent(self, event):
        if event.getName() == ChatLayer.EVENT_SEND_MESSAGE:
            target, text = self.getProp(self.PROP_SEND_MSG_DETAILS)
            logger.info('onEvent: Send out to WA [{0}]{1}'.format(target,text) )
            outgoingMessageProtocolEntity = TextMessageProtocolEntity(text, to=target)
            self.toLower(outgoingMessageProtocolEntity)
        elif event.getName() == ChatLayer.EVENT_PING:
            #if self.assertConnected():
            # print("onEvent: Ping")
            entity = PingIqProtocolEntity(to = YowConstants.DOMAIN)
            self.toLower(entity)
            self.pingcount += 1
            # print("Pingcount: {0}").format(self.pingcount)
            if self.pingcount >= 10:
                self.pingcount = 0
                logger.info('onEvent: Pingcount reached, do disconnect')
                self.disconnect_wa()
        elif event.getName() == ChatLayer.EVENT_TERMINATE:
            logger.info('onEvent: got ChatLayer.EVENT_TERMINATE')
            self.terminate = True
            self.disconnect_wa()
        elif event.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            logger.info('onEvent: Got EVENT_STATE_DISCONNECTED')
            if not self.terminate:
                time.sleep(10)
                logger.info('onEvent: Issueing EVENT_STATE_CONNECT')
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        else:
            logger.error('onEvent: Unknown Event: %s' % event.getName())

    def disconnect_wa(self):
        logger.info('disconnect_wa: Trigger disconnect')
        self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        logger.debug('onIQ: Got iq (Ping reply)')
        if self.pingcount > 0:
            self.pingcount -= 1

