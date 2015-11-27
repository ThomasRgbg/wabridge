#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
if sys.version_info < (3, 0):
    import sys
    reload(sys)
    sys.setdefaultencoding("UTF-8")

import argparse, datetime
import time, base64, string, os
import zmq
import logging
import pickle

logger = logging.getLogger(__name__)

class MSGObj(object):
    def __init__(self, source=None, dest=None, text=None, extra_data=None):
        self.source = source
        self.dest = dest
        self.text = text
        self.extra_data = extra_data

    def __str__(self):
        logger.debug('source {0}'.format(self.source))
        logger.debug('dest {0}'.format(self.dest))
        logger.debug('text {0}'.format(self.text))
        logger.debug('extra_data {0}'.format(self.extra_data))

        out = 'MSGObj: '
        out += self.source + '->' + self.dest + ': ' 
        out += '{0}'.format(self.text) + '(' + '{0}'.format(self.extra_data) + ')'
        return out


class ZMQReceiver(object):
    def __init__(self, login):
        socket = ('/tmp/whatsbridge_to_' +  login)
        self.zmq_context = zmq.Context.instance()
        self.zmq_sock = self.zmq_context.socket(zmq.SUB)
        if sys.version_info < (3, 0):
            self.zmq_sock.setsockopt(zmq.SUBSCRIBE, '')
        else:
            self.zmq_sock.setsockopt_string(zmq.SUBSCRIBE, '')
        self.zmq_sock.bind('ipc://' + socket)
        os.chmod(socket, 0o777)
        logger.info('__init__: Created ZMQ socket {0}'.format(socket))

    def poll_message(self):
        try:
            msg = self.zmq_sock.recv_pyobj(zmq.NOBLOCK)
        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                raise
                return (None, None, None, None)
        else:
            #logger.debug('poll_mesage: got raw_message %s' % raw_message)
            #try:
            #    msg = pickle.loads(raw_message)
            #except (pickle.UnpicklingError, pickle.PickleError):
            #    logger.info(u'poll_message: Garbage received via IPC: {0}'.format(raw_message) )
            #    return (None, None, None, None)
            #else:
            logger.info('poll_message: got via ZMQ: ' + str(msg) )
            # text = (msg.text.encode('utf-8'))
            text = msg.text
            return (msg.source, msg.dest, text, msg.extra_data)
        return (None, None, None, None)


class ZMQSender(object):
    def send_message(self, source, dest, text, extra_data=None):
        # source = xmpp-seite sender, zb whats_paula, dest = xmpp empfaenger, zb sophia@felsenkuschler.de
        msg = MSGObj(source, dest, text, extra_data)
        # datastream = pickle.dumps(data)

        self.context = zmq.Context.instance()
        self.sock = self.context.socket(zmq.PUB)
        logger.info('send_message: ' + str(msg))
        logger.debug("send_message: dispatcher: connect to ipc:///tmp/whatsbridge_to_{0}".format(source))
        self.sock.connect('ipc:///tmp/whatsbridge_to_' + source)
        # logger.debug(u"send_message: dispatcher: send %s" % str(datastream))
        # self.sock.send_unicode(datastream)
        self.sock.send_pyobj(msg)

