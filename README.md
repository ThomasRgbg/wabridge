wabridge
========

Bridge between XMPP chat servers and WA. 

## Warning
- Of course: Use at your own risk (of damage and frustration)
- These are just some scripts, based on [yowsup](https://github.com/tgalal/yowsup),  [SleekXMPP](https://github.com/fritzy/SleekXMPP) and [ZeroMQ](https://zeromq.org)
- A lot is just hardcoded and quick/dirty hacked, but no beautiful python code.
- It scales very bad, I wrote it to be able to talk some family relatives without really participating in WA. 
- I intend this not as highly supported project. I use it as it is and only dumped it here for your amusement. 

## Why ? 
My wonderful wife would like to chat to her mother. But she don't like to have a Smartphone. And her mother has a Iphone, but she is to far away to help her how to install a XMPP client. 

## How it works. (simplified)

```
+-----+                        +------+                           +--------+
|     |----[wa_user.py - 1]****|      |****[xmpp_user.py - MiL]===|        |=====
|     |                        | ZMQ  |                           |        |
| WA  |                        |      |                           |  XMPP  |
|     |                        |      |                           | Server |
|     |                        +------+                           |        |
|     |                               [XMPP client of my wife]====|        |
|     |---[Mother-in-law-Iphone]                                  +--------+
+-----+

-       is a connection to WA
*       is a IPC conection over ZMQ
=       is a XMPP connection

1       is a virtual WA useraccount 
MiL     is a virtual user on the XMPP server for the Mother-in-law-Iphone
```
So this is a pretty crappy concept, but it works for my purpose. For each (virtual) WA user there is a instance of wa_user.py running. It logs in into WA and waits for incomming messages. For each (virtual) XMPP user, there is a instance of xmpp_user.py running, logs in into the XMPP server and waits for a incoming message. 
So the point is, in the picture above the wa_user corresponds your own real xmpp-client, while the xmpp_user.py to the WA user you want talk to. 

Here in the example there is only one user on each side, but this works also with multiple users on both sides. But since there is own instance running, it scales very bad. 



