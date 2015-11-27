wabridge
========

Bridge between XMPP chat servers and WA. 

## Warning
- Of course: Use at your own risk (of damage and frustration)
- These are just some scripts, based on [yowsup](https://github.com/tgalal/yowsup),  [SleekXMPP](https://github.com/fritzy/SleekXMPP) and [ZeroMQ](https://zeromq.org)
- A lot is just hardcoded and quick/dirty hacked, but no beautiful python code.
- It scales very bad, I wrote it to be able to talk some family relatives without really participating in WA. 
- I intend this not as highly supported project. I use it as it is and only dumped it here for your amusement. 

## Why I started it ? 
My wonderful wife would like to chat to her mother. But she don't like to have a Smartphone. And her mother has a Iphone, but she is to far away to help her how to install a XMPP client. 

## Why I stopped it ?
WA blocked my account because other users WA client on their Iphone stopped working when I made some wrong UTF-8 convertions.
Finally I convinced the family to move away from WA, so no need to support this anymore. 

## How it works. (simplified)

```
                               +------+                           +--------+
                               |      |                           |        |
                               |      |                           |        |
                               |      |***[xmpp_component.py]=====|        |
+-----+                        |      |        (and / or )        |        |
|     |----[wa_user.py - 1]****|      |****[xmpp_user.py - MiL]===|        |
|     |                        | ZMQ  |                           |        |
| WA  |                        |      |                           |  XMPP  |
|     |                        |      |                           | Server |
|     |                        +------+                           |        |
|     |                                                           |        |
|     |                               [XMPP client of my wife]====|        |
|     |---[Mother-in-law-Iphone]                                  +--------+
+-----+

-       is a connection to WA
*       is a IPC conection over ZMQ
=       is a XMPP connection

1       is a virtual WA useraccount 
MiL     is a virtual user on the XMPP server for the Mother-in-law-Iphone
```

There are two WA representations in XMPP supported:

1. One XMPP user per WA contact:
This is a pretty crappy concept, but it works for my purpose. For each (virtual) WA user there is a instance of wa_user.py running. 
It logs in into WA and waits for incomming messages. For each (virtual) XMPP user, there is a instance of xmpp_user.py running, 
logs in into the XMPP server and waits for a incoming message. 
So the point is, in the picture above the wa_user corresponds your own real xmpp-client, while the xmpp_user.py to the WA user you want talk to. 

Here in the example there is only one user on each side, but this works also with multiple users on both sides. But since there is own instance running, it scales very bad. 

Each of the daemons uses a configfile, so multiple instances could be started. 

2. XMPP component:
This acts like a sub-server with many users attached to. You just need one instance of xmpp_component.py to start. But it need component support
on the XMPP server. In case you get message on WA from a user, it will automatically create a user with the WA phone number on the XMPP side. 
Disadavantage is, the user status on a component seems not to work, so the virtual users are most time "offline"

## Limitations

This is just a simple set of scripts and many things could be better, so [here](https://github.com/ThomasRgbg/wabridge/issues?q=is%3Aissue+is%3Alimiation) is a list of them.



