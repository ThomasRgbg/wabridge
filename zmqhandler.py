#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("UTF-8")

import argparse, sys, datetime
import time, base64, string, os
import zmq
import logging

logger = logging.getLogger(__name__)

class ZMQReceiver(object):
    def __init__(self, login):
        socket = ('/tmp/whatsbridge_to_%s' % login)
        self.zmq_context = zmq.Context.instance()
        self.zmq_sock = self.zmq_context.socket(zmq.SUB)
        self.zmq_sock.setsockopt(zmq.SUBSCRIBE, '')
        self.zmq_sock.bind('ipc://' + socket)
        os.chmod(socket, 0777)
        logger.info('__init__: Created ZMQ socket {0}'.format(socket))

    def poll_message(self):
        try:
            raw_message = self.zmq_sock.recv_unicode(zmq.NOBLOCK)
        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                raise
                return (None, None)
        else:
            msg = string.split(unicode(raw_message), '\/\/')
            if len(msg) == 2:
                logger.info(u"poll_message: got via ZMQ %s : %s" % (msg[0], msg[1]) )
                text = (msg[1].encode('utf-8'))
                target = msg[0]
                return (target, text)
            else:
                logger.info(u'poll_message: Garbage received via IPC: {0}'.format(raw_message) )
                return (None, None)
        return (None, None)


class ZMQSender(object):
    def send_message(self, source, dest, text):
        # source = xmpp-seite sender, zb whats_user1, dest = xmpp empfaenger, zb user1@xxxx.de
        self.context = zmq.Context.instance()
        self.sock = self.context.socket(zmq.PUB)
        logger.info('send_message: ' + source + '->' + dest + ': ' + text)
        logger.debug(u"send_message: dispatcher: connect to ipc:///tmp/whatsbridge_to_%s" % source)
        self.sock.connect(u'ipc:///tmp/whatsbridge_to_%s' % source)
        logger.debug(u"send_message: dispatcher: send %s\/\/%s" % (dest, text))
        self.sock.send_unicode(u'%s\/\/%s' % (dest, text))

