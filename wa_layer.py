#!/usr/bin/python3
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
from cli import Cli, clicmd

# Hack for UTF on Python 2.x:
import sys
if sys.version_info < (3, 0):
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

from yowsup.layers.protocol_receipts.protocolentities    import *
from yowsup.layers.protocol_groups.protocolentities      import *
from yowsup.layers.protocol_presence.protocolentities    import *
from yowsup.layers.protocol_messages.protocolentities    import *
from yowsup.layers.protocol_acks.protocolentities        import *
from yowsup.layers.protocol_ib.protocolentities          import *
from yowsup.layers.protocol_iq.protocolentities          import *
from yowsup.layers.protocol_contacts.protocolentities    import *
from yowsup.layers.protocol_chatstate.protocolentities   import *
from yowsup.layers.protocol_privacy.protocolentities     import *
from yowsup.layers.protocol_media.protocolentities       import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_profiles.protocolentities    import *
from yowsup.layers.axolotl.protocolentities.iq_key_get import GetKeysIqProtocolEntity
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup.common.tools import ModuleTools





from yowsup.common import YowConstants

logger = logging.getLogger(__name__)

class ChatLayer(Cli, YowInterfaceLayer):
    PROP_SEND_MSG_DETAILS  = "org.openwhatsapp.yowsup.prop.chat.sendmsg"
    EVENT_SEND_MESSAGE     = "org.openwhatsapp.yowsup.event.chat.sendmsg"
    EVENT_PING             = "org.openwhatsapp.yowsup.event.ping"
    EVENT_TERMINATE        = "org.openwhatsapp.yowsup.event.terminate"
    EVENT_DISCONNECT       = "org.openwhatsapp.yowsup.event.network.disconnect"

    def __init__(self):
        super(ChatLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.dispatcher = MsgDispatcher()
        self.pingcount = 0
        self.terminate = False

        self.accountDelWarnings = 0
        self.connected = False
        self.username = None
        self.sendReceipts = True
        self.iqs = {}

        #add aliases to make it user to use commands. for example you can then do:
        # /message send foobar "HI"
        # and then it will get automaticlaly mapped to foobar's jid
        self.jidAliases = {
            # "NAME": "PHONE@s.whatsapp.net"
        }


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

        logger.info('text: {0}'.format(text))
        logger.info('type: {0}'.format(type(text)))
        logger.info('hex: {0}'.format(":".join("{:02x}".format(ord(c)) for c in text) ))
        if message.isGroupMessage():
            text = text.encode('latin1').decode('utf-8')
            logger.info('text: {0}'.format(text))
            logger.info('type: {0}'.format(type(text)))
            logger.info('hex: {0}'.format(":".join("{:02x}".format(ord(c)) for c in text) ))

        text = formattedDate + ' ' + author + ': ' + text

        self.dispatcher.send2xmpp(wa_sender, wa_rcvr, text, None)

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

        self.dispatcher.send2xmpp(wa_sender, wa_rcvr, text, None)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        logger.debug('onReceipt: send ack')
        self.toLower(ack)

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()
        if notificationData:
            logger.info('onNotification' + notificationData)
        else:
            logger.info("onNotification: From :%s, Type: %s" % (self.jidToAlias(notification.getFrom()), notification.getType()))
        if self.sendReceipts:
            receipt = OutgoingReceiptProtocolEntity(notification.getId(), notification.getFrom())
            self.toLower(receipt)

    def onEvent(self, event):
        if event.getName() == ChatLayer.EVENT_SEND_MESSAGE:
            source, target, text, extra_data = self.getProp(self.PROP_SEND_MSG_DETAILS)
            original_sender = extra_data

            # Target myself, so it is a internal command
            if target == self.getProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS)[0] + '@s.whatsapp.net':
                logger.debug('onEvent: From {0} Got command: {1}'.format(original_sender, text))

                response = self.execCmd(text, original_sender)

                logger.debug('onEvent: Command response: {0}'.format(response))

                if response != None or response != '':
                    self.send2xmpp('wa_control', original_sender, response, None)

            # Target somebody else, send it wo WA
            else:
                logger.info('onEvent: Send message out to WA [{0}]{1}'.format(target,text) )
                outgoingMessageProtocolEntity = TextMessageProtocolEntity(text, to=target)
                self.toLower(outgoingMessageProtocolEntity)

        elif event.getName() == ChatLayer.EVENT_PING:
            if self.assertConnected():
                print("onEvent: Ping")
                entity = PingIqProtocolEntity(to = YowConstants.DOMAIN)
                self.toLower(entity)
                self.pingcount += 1
                print("Pingcount: {0}").format(self.pingcount)
                if self.pingcount >= 10:
                    self.pingcount = 0
                    logger.info('onEvent: Pingcount reached, do disconnect')
                    self.disconnect_wa()
        elif event.getName() == ChatLayer.EVENT_TERMINATE:
            logger.info('onEvent: got ChatLayer.EVENT_TERMINATE')
            self.terminate = True
            self.disconnect_wa()
        elif event.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED or event.getName() == ChatLayer.EVENT_DISCONNECT:
            logger.info('onEvent: Got EVENT_STATE_DISCONNECTED')
            if not self.terminate:
                time.sleep(10)
                logger.info('onEvent: Issueing EVENT_STATE_CONNECT')
                self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
        else:
            logger.error('onEvent: Unknown Event: %s' % event.getName())

    def send2xmpp(self, source, dest, text, extra_data=None):
        self.dispatcher.send2xmpp(source, dest, text, extra_data)


    def disconnect_wa(self):
        logger.info('disconnect_wa: Trigger disconnect')
        self.getStack().broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        if isinstance(entity, ListGroupsResultIqProtocolEntity): 
            print("ListGroupsResultIqProtocolEntity")
            print(entity)
            self.dispatcher.send2xmpp('wa_control', entity.getTo(), str(entity), None)

#        elif isinstance(entity, InfoGroupsResultIqProtocolEntity): 
            print("InfoGroupsResultIqProtocolEntity")
            print(entity)
            print(entity.getId())
            print(entity.getFrom())
            print(entity.getTo())
            self.dispatcher.send2xmpp('wa_control', self.getProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS)[0] + '@s.whatsapp.net', str(entity), None)

        else:
            logger.debug('onIQ: Got iq (Ping reply)')
            if self.pingcount > 0:
                self.pingcount -= 1

#################
# CLI Commands
################

    def aliasToJid(self, calias):
        for alias, ajid in self.jidAliases.items():
            if calias.lower() == alias.lower():
                return self.normalizeJid(ajid)

        return self.normalizeJid(calias)

    def jidToAlias(self, jid):
        for alias, ajid in self.jidAliases.items():
            if ajid == jid:
                return alias
        return jid

    def normalizeJid(self, number):
        if '@' in number:
            return number
        elif "-" in number:
            return "%s@g.us" % number

        return "%s@s.whatsapp.net" % number


    @clicmd("List all groups you belong to")
    def groups_list(self, user):
        logger.debug('groups_list()')

        def onSuccess(resultIqEntity, originalEntity, user):
            logger.debug('onGroupsResult(), resultIqEntity{0}'.format(resultIqEntity))
            result = str(resultIqEntity)
            self.send2xmpp('wa_control', user, result)

        def onError(resultIqEntity, originalEntity, user):
            logger.debug('onGroupsError(), resultIqEntity{0}'.format(resultIqEntity))
            self.send2xmpp('wa_control', user, 'List Groups: Error')

        successWrapper = lambda successEntity, originalEntity: onSuccess(successEntity, originalEntity, user)
        errorWrapper = lambda errorEntity, originalEntity: onError(errorEntity, originalEntity, user)

        self._sendIq(ListGroupsIqProtocolEntity(), successWrapper, errorWrapper)

        return ''


    @clicmd("Get group info")
    def group_info(self, user, group_jid='49170000000000-11111111111@g.us'):
        logger.debug('group_info({0})'.format(group_jid))

        def onSuccess(resultIqEntity, originalEntity, user):
            logger.debug('onGroupInfoResult(), resultIqEntity{0}'.format(resultIqEntity))
            result = str(resultIqEntity)
            self.send2xmpp('wa_control', user, result)

        def onError(resultIqEntity, originalEntity, user):
            logger.debug('onGroupInfoError(), resultIqEntity{0}'.format(resultIqEntity))
            self.send2xmpp('wa_control', user, 'Info Group: Error')

        successWrapper = lambda successEntity, originalEntity: onSuccess(successEntity, originalEntity, user)
        errorWrapper = lambda errorEntity, originalEntity: onError(errorEntity, originalEntity, user)

        self._sendIq(InfoGroupsIqProtocolEntity(self.aliasToJid(group_jid)), successWrapper, errorWrapper)
        return ''

    @clicmd("test command")
    def test(self, user, msg):
        logger.info('test() for {0},  got: {1}'.format(user, msg))
        self.send2xmpp('wa_control', user, 'via direct call: ' + msg)
        return 'via return: ' + msg





