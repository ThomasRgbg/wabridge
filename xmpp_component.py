#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sys
import logging
import getpass
import os
from optparse import OptionParser

import string

from zmqhandler import ZMQReceiver, ZMQSender
from dispatcher import MsgDispatcher

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
    import ConfigParser as configparser
else:
    raw_input = input
    import configparser

def get_config(config, section, option):
    if not config.has_option(section, option):
        print("option not found in configfile")
        return None
    value = config.get(section, option)
    if value is 'None':
        return None
    else:
        return value

class EchoComponent(ComponentXMPP):

    """
    A simple SleekXMPP component that echoes messages.
    """

    def __init__(self, jid, secret, server, port):
        self.logger = logging.getLogger(__name__)

        ComponentXMPP.__init__(self, jid, secret, server, port)

        # You don't need a session_start handler, but that is
        # where you would broadcast initial presence.

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)

        self.zmqsender = ZMQSender()
        self.zmqreceiver = ZMQReceiver('wa_component')

        self.schedule('Check ZMQ', 2, self.check_zmq, repeat=True)

        self.auto_authorize = True
        self.logger.info('__init__() done')
        self.dispatcher = MsgDispatcher()


    def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Since a component may send messages from any number of JIDs,
        it is best to always include a from JID.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        fromxmpp = str(msg['from'])
        fromxmpp = fromxmpp.split('/')[0]

        towhats = str(msg['to'])
        towhats = towhats.split('@')[0]

        if '-' in towhats:
            towhats += '@g.us'
        else:
            towhats += '@s.whatsapp.net'

        text = msg['body']

        fromwhats = self.dispatcher.translate(fromxmpp, 'xmpp')

        if fromwhats == None:
            self.logger.info("message(): could not match sender: {0}".format(fromxmpp))
            return

        self.logger.info("incoming_message: {0}/{1}->{2}:{3}".format(fromxmpp, fromwhats, towhats, text) )

        self.zmqsender.send_message(source=fromwhats, dest=towhats, text=text, extra_data=fromxmpp)

        # The reply method will use the messages 'to' JID as the
        # outgoing reply's 'from' JID.
        # msg.reply("Thanks for sending\n%(body)s" % msg).send()

    def send_textmessage(self, sender, to, body):
        self.send_message(mfrom = sender, mto=to, mbody=body, mtype='chat')
        self.logger.info('send_textmessage: [from: {0} to:{1}] {2}'.format(sender, to, body) )

    def check_zmq(self):
        (source, target, text, extra_data) = self.zmqreceiver.poll_message()
        if target:
            sender = extra_data.split('@')[0]
            sender += '@wa.server.de'
            self.logger.debug('check_zmq: got: [from: {0} to:{1}] {2}'.format(sender, target,text) )
            self.send_textmessage(sender=sender, to=target, body=text)
 

if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    optp.add_option("-s", "--server", dest="server",
                    help="server to connect to")
    optp.add_option("-P", "--port", dest="port",
                    help="port to connect to")

    optp.add_option("-c", "--config", dest="configfile",
                    help="configfile")
    optp.add_option("-l", "--logfile", dest="logfile",
                    help="logfile to use")

    opts, args = optp.parse_args()

    if opts.logfile is not None:
        console_log = open(opts.logfile, 'a', 1, encoding='utf-8')
        sys.stdout = console_log
        sys.stderr = console_log

    # Setup logging.
    logging.basicConfig(level = opts.loglevel, datefmt='%H:%M:%S', format='%(asctime)s %(levelname)s:%(name)s:%(funcName)s:%(message)s')

    configfile = opts.configfile

    config = configparser.RawConfigParser()
    if os.path.isfile(configfile):
        config.read(configfile)
    else:
        print("No Configfile found at {0}".format(configfile))
        sys.exit(1)

    if opts.jid is None:
        opts.jid = get_config(config, 'Credentials', 'jid')
    if opts.password is None:
        opts.password = get_config(config, 'Credentials', 'password')
    if opts.server is None:
        opts.server = get_config(config, 'Server', 'host')
    if opts.port is None:
        opts.port = get_config(config, 'Server', 'port')

    # Setup the EchoComponent and register plugins. Note that while plugins
    # may have interdependencies, the order in which you register them does
    # not matter.
    xmpp = EchoComponent(opts.jid, opts.password, opts.server, opts.port)
    xmpp.registerPlugin('xep_0030') # Service Discovery
    xmpp.registerPlugin('xep_0004') # Data Forms
    xmpp.registerPlugin('xep_0060') # PubSub
    xmpp.registerPlugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
