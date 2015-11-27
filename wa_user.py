#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Main program for whatsbridge - whatsapp side. 
# Uses yowsup (from https://github.com/tgalal/yowsup)
#      zmq / python-zmq (from http://zeromq.org)
#      whatsapp_layer.py 
#
# Based on https://github.com/tgalal/yowsup/blob/master/yowsup/demos/echoclient/stack.py


# Hack for UTF on Python 2.x:
import sys
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding("UTF-8")

from zmqhandler import ZMQReceiver

from wa_layer import ChatLayer
from yowsup.layers.network                     import YowNetworkLayer
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStackBuilder
from yowsup import env
from yowsup.env import S40YowsupEnv

from optparse import OptionParser
if sys.version_info < (3, 0):
    import ConfigParser as configparser
else:
    import configparser

import logging
import time
import os

logger = logging.getLogger(__name__)

def get_config(config, section, option):
    if not config.has_option(section, option):
        return None
    value = config.get(section, option)
    if value is 'None':
        return None
    else:
        return value

if __name__==  "__main__":

    show_raw_packets = True
    all_output_to_file = False
    encryptionEnabled = True

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

    optp.add_option("-l", "--logfile", dest="logfile",
                    help="logfile to use")

    optp.add_option("-c", "--config", dest="configfile",
                    help="configfile")
 
    opts, args = optp.parse_args()

    if opts.logfile is not None:
        if sys.version_info < (3, 0):
            console_log = open(opts.logfile, 'a', 1)
        else:
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

    if not encryptionEnabled:
        env.CURRENT_ENV = S40YowsupEnv()

    stackBuilder = YowStackBuilder()

    stack = stackBuilder\
        .pushDefaultLayers(encryptionEnabled)\
        .push(ChatLayer)\
        .build()

    zmq = ZMQReceiver(get_config(config, 'Credentials', 'user') + '@s.whatsapp.net')

    stack.setCredentials( (get_config(config, 'Credentials', 'user'),get_config(config, 'Credentials', 'password')) )

    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))   #sending the connect signal

    pingcount = 0
    try: 
        while True:
            # Loop: - Let Yowsup libs run only 2 seconds, 
            #       - Check for incomming messages via ZMQ, if yes, pass them out 
            #         per event to whatsup_layer.py 
            #       - Every 10th iteraton, send a ping event wo whatsup_layer.py
            # logger.debug('(re)starting main loop')
            stack.loop(timeout=2, count=1) # Let the taskloop run one time for 2 seconds 

            (source, target, text, extra_data) = zmq.poll_message()


            if target:
                text = text.encode('utf-8')
                stack.setProp(ChatLayer.PROP_SEND_MSG_DETAILS, (source, target, text, extra_data))
                stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_SEND_MESSAGE)) 

            #pingcount += 1

            #if pingcount > 40:
                #pingcount=0
                # stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_PING)) 

            # Angst-delay
            time.sleep(0.5)

    # if CTRL-C, send a disconnect. Otherwise WA will let us not in the next time
    except KeyboardInterrupt:
        stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_TERMINATE))   #sending the disconnect signal

