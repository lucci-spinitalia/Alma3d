#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import signal
import threading
import os
import sys
from twisted.internet import protocol, reactor


class CanDebugger(protocol.ProcessProtocol):
    """Gestione del debugger CANOPEN
    Implementa il wrapper per il controllo del debugger CANOPEN, che viene qui creato un un processo
    esterno, catturando opportunamente STDIN e STDOUT.
    """

    def __init__(self):

        logger.info("Initializing ALMA_Canopen class")

        self.data = ""
        self.last_command = ""
        #self.tripod = tripod

    def sendCommand(self, command):

        if self.connected:
            self.transport.write("%s\n" % command)
            self.last_command = command
            logger.info("To Canopen '%s\\n'" % command)

    def connectionMade(self):

        logger.info("ConnectionMade with CANOpen!")

        # Avvio il thread per la lettura delle posizioni
        #self.tripod.isReading = True
        #self.tripod.receiver_thread = threading.Thread(target=self.tripod.stream_reader)
        #self.tripod.receiver_thread.setDaemon(True)
        #self.tripod.receiver_thread.start()

    def traslate_ims(self, interpolation_mode_status):

        if interpolation_mode_status & 0x8000:
            temp = "Run "
        else:
            temp = "... "

        if interpolation_mode_status & 0x4000:
            temp += "U "
        else:
            temp += ". "

        if interpolation_mode_status & 0x2000:
            temp += "O "
        else:
            temp += ". "

        if interpolation_mode_status & 0x1000:
            temp += "Drv "
        else:
            temp += "... "

        if interpolation_mode_status & 0x800:
            temp += "E_PI "
        else:
            temp += ".... "

        if interpolation_mode_status & 0x400:
            temp += "E_T "
        else:
            temp += "... "

        if interpolation_mode_status & 0x200:
            temp += "Rdy "
        else:
            temp += "... "

        if interpolation_mode_status & 0x100:
            temp += "Pend "
        else:
            temp += ".... "

        if interpolation_mode_status & 0x80:
            temp += "Res "
        else:
            temp += "... "

        if interpolation_mode_status & 0x40:
            temp += "E_PT "
        else:
            temp += ".... "

        return temp

    def traslate_mop(self, modes_of_operation):

        if modes_of_operation == -3:
            return "Step and Direction input ({})".format(modes_of_operation)
        elif modes_of_operation == -2:
            return "Follow quadrature encoder input ({})".format(modes_of_operation)
        elif modes_of_operation == -1:
            return "Reserved ({})".format(modes_of_operation)
        elif modes_of_operation == 0:
            return "Null ({})".format(modes_of_operation)
        elif modes_of_operation == 1:
            return "PP mode"
        elif modes_of_operation == 2:
            return "Not supported ({})".format(modes_of_operation)
        elif modes_of_operation == 3:
            return "PV mode"
        elif modes_of_operation == 4:
            return "TQ mode"
        elif modes_of_operation == 5:
            return "Reserved ({})".format(modes_of_operation)
        elif modes_of_operation == 6:
            return "HM mode"
        elif modes_of_operation == 7:
            return "IP mode"
        else:
            return "Not supported ({})".format(modes_of_operation)

    def outReceived(self, data):
        """Sono stati ricevuti bytes su STDOUT dal sotto-processo
        Il sotto-processo ha appena inviato su stdout delle informazioni, che rigiro a chi connesso via TCP"""
        #logger.info("From Canopen '%s'" % data.replace("\n","\\n"))
        for line in data.split("\n"):
            temp = line.split()
            if len(temp) > 0:
                if temp[1] == "180":
                    # COB-ID 180: "node id" (8-bit), "status word" (16-bit), "interpolation mode status" (16-bit), "modes of operation" (8-bit)
                    node_id = temp[3]
                    status_word = int(temp[5] + temp[4], 16)
                    interpolation_mode_status = int(temp[7] + temp[6], 16)
                    interpolation_mode_status_bits = "{:011b}".format(interpolation_mode_status / 32)
                    interpolation_mode_status_free_bits = int(temp[7] + temp[6], 16) & 0x1F
                    modes_of_operation = int(temp[8])
                    print "{} {:016b} - {} \ {:02d} \ {} - {}   {}".format(
                        node_id,
                        status_word,
                        interpolation_mode_status_bits,
                        interpolation_mode_status_free_bits,
                        self.traslate_ims(interpolation_mode_status),
                        self.traslate_mop(modes_of_operation),
                        line
                    )

                elif temp[1] == "380":
                    # MAP TPDO 3 (COB-ID 380) to receive high resolution timestamp
                    timestamp = long(temp[6] + temp[5] + temp[4] + temp[3], 16)
                    print "Timestamp {:012d} -------------------------------- {}".format(
                        timestamp,
                        line
                    )
                    # MAP TPDO 2 (COB-ID 280) to transmit "node id" (8-bit), "position actual value" (32-bit)
                    # MAP RPDO 1 (COB-ID 200 + nodeid) to receive "Interpolation Time Index" (8-bit)" (0x06c2 sub2)
                    # MAP RPDO 2 (COB-ID 300 + nodeid) to receive "Interpolation Time Units" (8-bit)" (0x06c2 sub1)

                    # MAP RPD0 4 (COB-ID 500 + nodeid) to receive "Control Word (16-bit)" (0x6040 sub0)

                    # MAP TPDO 1 (COB-ID 180) to transmit "node id" (8-bit), "status word" (16-bit), "interpolation mode status" (16-bit)
                    # MAP TPDO 2 (COB-ID 280) to transmit "node id" (8-bit), "position actual value" (32-bit)

                    # MAP RPDO 1 (COB-ID 200 + nodeid) to receive "Interpolation Time Index" (8-bit)" (0x60c2 sub2)
                    # MAP RPDO 2 (COB-ID 300 + nodeid) to receive "Interpolation Time Units" (8-bit)" (0x60c2 sub1)
                    # MAP RPDO 3 (COB-ID 400 + nodeid) to receive "Interpolation Data" (32-bit)" (0x60c1 sub1)
                    # MAP RPD0 4 (COB-ID 500 + nodeid) to receive "Control Word (16-bit)" (0x6040 sub0)
                    # MAP RPDO 5 (COB-ID 380) to receive high resolution timestamp
                elif temp[1] == "477":
                    # MAP RPDO 3 (COB-ID 400 + nodeid) to receive "Interpolation Data" (32-bit)" (0x06c1 sub1)
                    pos = long(temp[6] + temp[5] + temp[4] + temp[3], 16)
                    print "Pos 77 {:012d}                                     {}".format(
                        pos,
                        line
                    )
                elif temp[1] == "478":
                    pos = long(temp[6] + temp[5] + temp[4] + temp[3], 16)
                    print "Pos 78 {:012d}                                     {}".format(
                        pos,
                        line
                    )
                elif temp[1] == "479":
                    pos = long(temp[6] + temp[5] + temp[4] + temp[3], 16)
                    print "Pos 79 {:012d}                                     {}".format(
                        pos,
                        line
                    )
                elif temp[1] == "47A":
                    pos = long(temp[6] + temp[5] + temp[4] + temp[3], 16)
                    print "Pos 7A {:012d}                                     {}".format(
                        pos,
                        line
                    )
                else:
                    print "                                                        {}".format(line)


    def errReceived(self, data):
        """Sono stati ricevuti bytes su STDERR dal sotto-processo
        Il sotto-processo ha appena inviato su stderr delle informazioni"""

        logger.info("errReceived! with %d bytes! %s" % (len(data), data))

    def inConnectionLost(self):

        logger.info("inConnectionLost! stdin is closed! (we probably did it)")

    def outConnectionLost(self):

        logger.info("outConnectionLost! The child closed their stdout!")

    def errConnectionLost(self):

        logger.info("errConnectionLost! The child closed their stderr.")

    def processExited(self, reason):

        if reason.value.exitCode:
            logger.info("processExited, exit code %d" % (reason.value.exitCode,))
        else:
            logger.info("processExited")

    def processEnded(self, reason):

        if reason.value.exitCode:
            logger.info("processEnded, exit code %d" % (reason.value.exitCode,))
        else:
            logger.info("processEnded")

def start_can():

    # Avvio il server CANOPEN
	# usePTY serve ad evitare l'ECHO
	# INFO: uso stdbuf per evitare il buffering dell'output se non in terminale
	reactor.spawnProcess(can_dbg, "/usr/bin/candump", args=["/usr/bin/candump", "can0,400:700,300:700,180:7FF"], env=os.environ, usePTY=False)


if __name__ == '__main__':

    logger = logging.getLogger('root')
    FORMAT = "[%(filename)s:%(lineno)3s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    # Called on process interruption
    def end_process(signalnum = None, handler = None):
        # Chiude il processo di comunicazione con i motori se attivo
        if can_dbg:
            can_dbg.transport.closeStdin()
            reactor.stop()

    # Install the exit handler
    signal.signal(signal.SIGINT, end_process)

    # Start the CANOPEN server
    can_dbg = CanDebugger()
    start_can()

    # Avvio il reattore!
    reactor.run()
