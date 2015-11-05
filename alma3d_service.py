#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://blogofterje.wordpress.com/2012/01/14/optimizing-fs-on-sd-card/

import signal
import logging
from twisted.internet import protocol, reactor, task

import alma3d


if __name__ == '__main__':

    # Configuro il loggin
    #FORMAT = "%(asctime)-15s %(clientip)s %(user)-8s %(message)s"
    #logging.basicConfig(format=FORMAT)
    #d = {'clientip': '192.168.0.1', 'user': 'fbloggs'}
    #logging.warning("Protocol problem: %s", "connection reset", extra=d)
    logger = logging.getLogger('root')
    FORMAT = "[%(filename)s:%(lineno)3s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    tripod = alma3d.Tripod()

    # Called on process interruption. Set all pins to "Input" default mode.
    def endProcess(signalnum = None, handler = None):
        tripod.cleanup()
        #sys.exit()
        
    # Install the exit handler
    signal.signal(signal.SIGINT, endProcess)
    
    # Start the CANOPEN server
    tripod.start_canopen()

    # Avvio il server TCP dei comandi, delle posizioni e della ricerca IP
    reactor.listenMulticast(10000, alma3d.DiscoveryProtocol(), listenMultiple=True)
    reactor.listenTCP(10001, alma3d.PositionFactory(tripod))
    reactor.listenTCP(10002, alma3d.ControlFactory(tripod))

    # Avvio il reattore!
    reactor.run()
