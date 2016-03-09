# -*- coding: utf-8 -*-

from twisted.internet import protocol
from PositionProtocol import PositionProtocol
import logging


class PositionFactory(protocol.Factory):
    """Factory di gestione del protocollo di invio delle posizioni ALMA"""

    def __init__(self, tripod):
        # Devo impedire il collegamento multiplo!
        self.tripod = tripod
        self.tripod.position_factory = self
        self.tripod.isPosClientConnected = False
        self.tripod.posConnectedAddress = ""
    
    def buildProtocol(self, addr):
        self.tripod.almaPositionProtocol = PositionProtocol(self.tripod)
        self.tripod.posConnectedAddress = addr
        logging.info("Position connection request from %s" % addr)
        return self.tripod.almaPositionProtocol
