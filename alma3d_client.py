#!/usr/bin/env python

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor

class MulticastPingClient(DatagramProtocol):
    """
    Servizio di ricerca del dipositivo tripode
    Basato sul Multicast per permettere il passaggio attraverso router.
    Il gruppo multicast assegnato e' 228.0.0.5, la porta e' la 10000.
    Il protocollo e' semplice, il client invia "Ping Spinitalia_ALMA_3D", il server
    risponde "Spinitalia_ALMA_3D: Pong", direttamente all'indirizzo del mittente,
    con il suo indirizzo.
    """
	
    def startProtocol(self):

        print "ALMA 3D di SpinItalia s.r.l. ver: 1.0"
        print "Esempio di ricerca IP"

        # Si unisce ad un gruppo multicast specifico
        self.transport.joinGroup("228.0.0.5")

        # Invio il ping
        self.transport.write('Ping Spinitalia_ALMA_3D', ("228.0.0.5", 10000))

    def datagramReceived(self, datagram, address):

        if datagram == "Pong Spinitalia_ALMA_3D":
          print "ALMA 3D IP: %s" % address[0]
          reactor.stop()

reactor.listenMulticast(10000, MulticastPingClient(), listenMultiple=True)
reactor.run()
