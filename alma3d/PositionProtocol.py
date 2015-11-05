# -*- coding: utf-8 -*-
from twisted.protocols.basic import protocol
import logging
import time
import traceback
import sys


class PositionProtocol(protocol.Protocol):
    """Protocollo per l'invio delle posizioni ALMA"""

    def __init__(self, tripod):

        self.tripod = tripod
        self.is_loopincall_active = False
        #self.posSender = task.LoopingCall(self.sendPosition)

    def connectionMade(self):
        self.tripod.position_factory.numProtocols = self.tripod.position_factory.numProtocols + 1
        #self.posSender = task.LoopingCall(self.sendPosition)
        #self.posSender.start(0.01)
        #self.is_loopincall_active = True
        logging.info("Welcome! There are currently %d open connections" % (self.tripod.position_factory.numProtocols))

    def connectionLost(self, reason):
        #self.tripod.almaStreamProtocol.posSender.stop()
        self.tripod.position_factory.numProtocols = self.tripod.position_factory.numProtocols - 1

    def sendPosition(self):

        if all([self.tripod.canStatus == 4, self.is_loopincall_active]):
            #self.posSender.stop()
            self.is_loopincall_active = False

        roll = 0
        pitch = 0
        yaw = 0
        max_step = 320000    # Sono +/-0.4mt, che con 8000 step / 10 mm fanno +/- 320000
        max_yaw_step = 2147483648
        comment = ""
        #logging.info("[{:6d}, {:6d}, {:6d}] -> [{:09.6f}, {:09.6f}, {:09.6f}]".format(
        #    long(self.tripod.motorPos[self.tripod.motorsAddress[1]]),
        #    long(self.tripod.motorPos[self.tripod.motorsAddress[2]]),
        #    long(self.tripod.motorPos[self.tripod.motorsAddress[3]]),
        #    float(self.tripod.motorPos[self.tripod.motorsAddress[1]]) / 800,
        #    float(self.tripod.motorPos[self.tripod.motorsAddress[2]]) / 800,
        #    float(self.tripod.motorPos[self.tripod.motorsAddress[3]]) / 800))

        if len(self.tripod.motorsAddress) < 4:
            #logging.info("No motors found")
            pass
        elif not self.tripod.isCentered:
            #logging.info("Not centered")
            pass
        elif self.tripod.isImporting:
            roll = 0.0
            pitch = 0.0
            yaw = 0.0
            comment = "line {:06d}".format(self.tripod.currentLine)

        elif (long(self.tripod.motorPos['120']) > max_step) or (long(self.tripod.motorPos['120']) < -max_step):

            logging.info("Limite del giunto 120 superato, {} < {} < {}".format(-max_step, self.tripod.motorPos['120'],
                                                                              max_step))

        elif (long(self.tripod.motorPos['121']) > max_step) or (long(self.tripod.motorPos['121']) < -max_step):

            logging.info("Limite del giunto 121 superato, {} < {} < {}".format(-max_step, self.tripod.motorPos['121'],
                                                                              max_step))

        elif (long(self.tripod.motorPos['122']) > max_step) or (long(self.tripod.motorPos['122']) < -max_step):

            logging.info("Limite del giunto 122 superato, {} < {} < {}".format(-max_step, self.tripod.motorPos['122'],
                                                                              max_step))

        elif (long(self.tripod.motorPos['119']) > max_yaw_step) or (long(self.tripod.motorPos['119']) < -max_yaw_step):

            logging.info("Limite del giunto 119 superato, {} < {} < {}".format(-max_step, self.tripod.motorPos['119'],
                                                                              max_step))

        else:

            start = time.time()
            self.tripod.kinematic.find_solution_Z1Y2X3([-float(self.tripod.motorPos['120']) / self.tripod.kinematic.mt_to_step,
                                                      -float(self.tripod.motorPos['121']) / self.tripod.kinematic.mt_to_step,
                                                      -float(self.tripod.motorPos['122']) / self.tripod.kinematic.mt_to_step,
                                                      float(self.tripod.motorPos['119']) / self.tripod.kinematic.radians_to_step])
            process_time = (time.time() - start) * 1000
            roll = self.tripod.kinematic.roll
            pitch = self.tripod.kinematic.pitch
            yaw = self.tripod.kinematic.yaw
            comment = "{:03d} / {:04.1f} ms".format(self.tripod.kinematic.cycles, process_time)

            if self.tripod.canStatus == '8':

                self.tripod.last_sim_time += float(self.tripod.posTime) / 1000.0
                self.tripod.last_sim_file.write("{};{};{};{};{};{};{};{};{}\n".format(
                            int(self.tripod.mex_counter),
                            self.tripod.last_sim_time,
                            roll,
                            pitch,
                            yaw,
                            float(self.tripod.motorPos['119']),
                            float(self.tripod.motorPos['120']),
                            float(self.tripod.motorPos['121']),
                            float(self.tripod.motorPos['122'])))

        # R12.321;P-2.23;Y0;AS0;T10;C0;avvio simulazione 33c995835f28604045b1256f645c9195
        #self.transport.write("R{:+07.2f};P{:+07.2f};Y{:+08.2f};AS{};T{:02d};C{:03d};{}\n".format(
        #    roll,
        #    pitch,
        #    yaw,
        #    self.tripod.canStatus,
        #    int(self.tripod.posTime),
        #    int(self.tripod.OpProgress),
        #    comment))

        try:
            self.transport.write("{:10d};{:+07d};{:+07d};{:+07d};{:+07d};{:+08.3f};{:+08.3f};{:+09.3f};AS{};T{:04.1f};C{:03d};{}\n".format(
                int(self.tripod.mex_counter),
                int(self.tripod.motorPos['119']),
                int(self.tripod.motorPos['120']),
                int(self.tripod.motorPos['121']),
                int(self.tripod.motorPos['122']),
                roll,
                pitch,
                yaw,
                self.tripod.canStatus,
                float(self.tripod.posTime),
                int(self.tripod.OpProgress),
                comment))
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Impossibile inviare lo stato (%s)" % sys.exc_info()[0])
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)

