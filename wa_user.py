#!/usr/bin/python 

# Main program for whatsbridge - whatsapp side. 
# Uses yowsup (from https://github.com/tgalal/yowsup)
#      zmq / python-zmq (from http://zeromq.org)
#      whatsapp_layer.py 
#
# Based on https://github.com/tgalal/yowsup/blob/master/yowsup/demos/echoclient/stack.py

from zmqhandler import ZMQReceiver

from wa_layer import ChatLayer
from yowsup.layers.auth                        import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages           import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts           import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks               import YowAckProtocolLayer
from yowsup.layers.network                     import YowNetworkLayer
from yowsup.layers.coder                       import YowCoderLayer
from yowsup.stacks import YowStack, YOWSUP_FULL_STACK_DEBUG, YOWSUP_FULL_STACK
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStack, YOWSUP_CORE_LAYERS

import logging
import time
import sys

logger = logging.getLogger(__name__)

CREDENTIALS = ("49123456", "xxxxxxxxxxxxxxxxxxx=") # TODO: make commandline parameter

if __name__==  "__main__":

    show_raw_packets = True
    all_output_to_file = False

    if all_output_to_file:
        console_log = open('wa_user.log', 'w', 0)
        sys.stdout = console_log
        sys.stderr = console_log

    logging.basicConfig(level = logging.DEBUG) # TODO: Make commandline parameter

    if show_raw_packets:
        layers = ( (ChatLayer,) + YOWSUP_FULL_STACK_DEBUG)
    else:
        layers = ( (ChatLayer,) + YOWSUP_FULL_STACK)

    zmq = ZMQReceiver(CREDENTIALS[0] + '@s.whatsapp.net')

    stack = YowStack(layers)
    stack.setProp(YowAuthenticationProtocolLayer.PROP_CREDENTIALS, CREDENTIALS)         #setting credentials
    stack.setProp(YowNetworkLayer.PROP_ENDPOINT, YowConstants.ENDPOINTS[0])    #whatsapp server address
    stack.setProp(YowCoderLayer.PROP_DOMAIN, YowConstants.DOMAIN)              
    stack.setProp(YowCoderLayer.PROP_RESOURCE, YowConstants.RESOURCE)          #info about us as WhatsApp client

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
                stack.setProp(ChatLayer.PROP_SEND_MSG_DETAILS, (target, text))
                stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_SEND_MESSAGE)) 

            pingcount += 1

            if pingcount > 10:
                pingcount=0
                stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_PING)) 

            # Angst-delay
            time.sleep(0.1)

    # if CTRL-C, send a disconnect. Otherwise WA will let us not in the next time
    except KeyboardInterrupt:
        stack.broadcastEvent(YowLayerEvent(ChatLayer.EVENT_TERMINATE))   #sending the disconnect signal

