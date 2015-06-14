#!/usr/bin/python 

# Main program for whatsbridge - whatsapp side. 
# Uses yowsup (from https://github.com/tgalal/yowsup)
#      zmq / python-zmq (from http://zeromq.org)
#      whatsapp_layer.py 
#
# Based on https://github.com/tgalal/yowsup/blob/master/yowsup/demos/echoclient/stack.py

from zmqhandler import ZMQReceiver

from wa_layer import ChatLayer
from yowsup.layers.network                     import YowNetworkLayer
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStackBuilder
from yowsup import env
from yowsup.env import S40YowsupEnv

from optparse import OptionParser

import logging
import time
import sys

logger = logging.getLogger(__name__)

CREDENTIALS = ("491711234567", "ABCDEDFADFADFADDFADFADF=") # TODO: make commandline parameter

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

    opts, args = optp.parse_args()

    if opts.logfile is not None:
        console_log = open(opts.logfile, 'w', 0)
        sys.stdout = console_log
        sys.stderr = console_log

    # Setup logging.
    logging.basicConfig(level = opts.loglevel, datefmt='%H:%M:%S', format='%(asctime)s %(levelname)s:%(name)s:%(funcName)s:%(message)s')

    if not encryptionEnabled:
        env.CURRENT_ENV = S40YowsupEnv()

    stackBuilder = YowStackBuilder()

    stack = stackBuilder\
        .pushDefaultLayers(encryptionEnabled)\
        .push(ChatLayer)\
        .build()

    zmq = ZMQReceiver(CREDENTIALS[0] + '@s.whatsapp.net')

    stack.setCredentials(CREDENTIALS)

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

            (target, text) = zmq.poll_message()
            if target:
                # pass
                stack.setProp(ChatLayer.PROP_SEND_MSG_DETAILS, (target, text))
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

