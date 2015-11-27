#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hack for UTF on Python 2.x:
import sys
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding("UTF-8")
else:
    raw_input = input

import logging
import getpass
import string

from optparse import OptionParser

import os.path
import sys
import configparser

from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout

from dispatcher import MsgDispatcher
from zmqhandler import ZMQReceiver

class ChatBot(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.logger = logging.getLogger(__name__)
        self.dispatcher = MsgDispatcher()
        self.zmq = ZMQReceiver(jid)

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.incoming_message)

        # If you wanted more functionality, here's how to register plugins:
        # self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # XMPP Ping

        # Here's how to access plugins once you've registered them:
        # self['xep_0030'].add_feature('echo_demo')

        # If you are working with an OpenFire server, you will
        # need to use a different SSL version:
        # import ssl
        # self.ssl_version = ssl.PROTOCOL_SSLv3

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        # Most get_*/set_* methods from plugins use Iq stanzas, which
        # can generate IqError and IqTimeout exceptions
        #
        # try:
        #     self.get_roster()
        # except IqError as err:
        #     logging.error('There was an error getting the roster')
        #     logging.error(err.iq['error']['condition'])
        #     self.disconnect()
        # except IqTimeout:
        #     logging.error('Server is taking too long to respond')
        #     self.disconnect()

        # Check for new incomming message via ZMQ every 2 seconds
        # TODO: In case of a reconnect, clean up first the old entry
        self.schedule('Check ZMQ', 2, self.check_zmq, repeat=True)
        self.logger.info('session_start done')


    def incoming_message(self, msg):
        #if msg['type'] in ('chat', 'normal'):
        #    msg.reply("Thanks for sending\n%(body)s" % msg).send()
        fromxmpp = str(msg['from'])
        fromxmpp = fromxmpp.split('/')[0]
        toxmpp = str(msg['to'])
        toxmpp = toxmpp.split('/')[0]
        text = msg['body']

        if fromxmpp == 'groupname@server.de':
            self.logger.debug('incomming_message: replace {0} with {1}'.format(fromxmpp,msg['subject']) )
            fromxmpp = msg['subject']

        self.logger.info("incoming_message: {0}->{1}:{2}".format(fromxmpp, toxmpp, text) )
        self.dispatcher.send2whats(fromxmpp, toxmpp, text, fromxmpp)

    def send_textmessage(self, to, body):
        self.send_message(mto=to, mbody=body, mtype='chat')
        self.logger.info('send_textmessage: [to:{0}] {1}'.format(to,body) )

    def check_zmq(self):
        (source, target, text, extra_data) = self.zmq.poll_message()
        if target:
            self.logger.debug('check_zmq: got: [to:{0}] {1}'.format(target,text) )
            self.send_textmessage(to=target, body=text)

def get_config(config, section, option):
    if not config.has_option(section, option):
        return None
    value = config.get(section, option)
    if value is 'None':
        return None
    else:
        return value

if __name__ == '__main__':
    all_output_to_file = True


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

    if opts.jid is None:
        print("No username found in configfile")
        sys.exit(1)
    if opts.password is None:
        print("No password found in configfile")
        sys.exit(1)

    try:
        xmpp = ChatBot(opts.jid, opts.password)
        if xmpp.connect(('server.de','5222')):
            xmpp.process(block=True)
        else:
            print('Unable to connect')
    # if CTRL-C, send a disconnect.
    except KeyboardInterrupt:
        xmpp.disconnect(wait=True)

