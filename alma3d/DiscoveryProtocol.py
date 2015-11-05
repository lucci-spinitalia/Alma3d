from twisted.internet.protocol import DatagramProtocol


class DiscoveryProtocol(DatagramProtocol):
    """
    Servizio di ricerca del dipositivo tripode
    Basato sul Multicast per permettere il passaggio attraverso router.
    Il gruppo multicast assegnato e' 228.0.0.5
    Il protocollo e' semplice, il client invia "Ping Spinitalia_ALMA3D", il server
    risponde "Spinitalia_ALMA3D: Pong", direttamente all'indirizzo del mittente,
    con il suo indirizzo.
    """

    def startProtocol(self):
        """
        Chiamata dopo che il protocollo inizia ad ascoltare!
        """
        print "ALMA 3D by SpinItalia s.r.l. ver: 1.0"
        print "Servizio di ricerca IP avviato..."
        # Aumento il TTL per superare routers
        self.transport.setTTL(5)
        # Si unisce ad un gruppo multicast specifico
        self.transport.joinGroup("228.0.0.5")

    def datagramReceived(self, datagram, address):
        print "Ping %s ricevuto da %s" % (repr(datagram), repr(address))
        if datagram == "Ping Spinitalia_ALMA_3D":
            # Invece di rispondere in multicast, inviamo una risposta direttamente
            # al client via unicast alla porta di origine, per rendersi raggiungibile
            self.transport.write("Pong Spinitalia_ALMA_3D", address)
