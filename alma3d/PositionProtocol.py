# -*- coding: utf-8 -*-
from twisted.protocols.basic import protocol
import logging
import traceback
import sys


class PositionProtocol(protocol.Protocol):
    """Protocollo per l'invio delle posizioni ALMA"""

    def __init__(self, tripod):

        self.tripod = tripod

    def connectionMade(self):

        # Controllo che non sia gia' connesso qualcuno
        if self.tripod.isPosClientConnected:
            logging.info("Position connection request but already connected from %s" % self.tripod.posConnectedAddress)
            self.sendLine("AERR 91: Connessione posizioni gia' effettuata dall'indirizzo Ip {}".format(
                self.tripod.posConnectedAddress)
            )
            self.transport.loseConnection()
            return
        else:
            logging.info("Connection request from %s" % self.tripod.posConnectedAddress)
            self.tripod.isPosClientConnected = True

    def connectionLost(self, reason=None):

        logging.info("Connection lost with TCP position client ({})!".format(reason))

        self.tripod.isPosClientConnected = False
        self.tripod.posConnectedAddress = ""

    def send_position(self):

        roll = 0.0
        pitch = 0.0
        yaw = 0.0
        v_roll = 0.0
        v_pitch = 0.0
        v_yaw = 0.0
        max_step = 320000    # Sono +/-0.4mt, che con 8000 step / 10 mm fanno +/- 320000
        max_yaw_step = 2147483648

        if self.tripod.isImporting:

            # Quando importo un file, gli angoli e le velocità sono sempre nulle
            pass

        elif (long(self.tripod.motorPos['120']) > max_step) or (long(self.tripod.motorPos['120']) < -max_step):

            # Quando i giunti sono oltre i limiti, le velocità e gli angoli sono sempre nulli
            logging.info("Limite del giunto 120 superato, {} < {} < {}".format(
                -max_step, self.tripod.motorPos['120'], max_step))

        elif (long(self.tripod.motorPos['121']) > max_step) or (long(self.tripod.motorPos['121']) < -max_step):

            logging.info("Limite del giunto 121 superato, {} < {} < {}".format(
                -max_step, self.tripod.motorPos['121'], max_step))

        elif (long(self.tripod.motorPos['122']) > max_step) or (long(self.tripod.motorPos['122']) < -max_step):

            logging.info("Limite del giunto 122 superato, {} < {} < {}".format(
                -max_step, self.tripod.motorPos['122'], max_step))

        elif (long(self.tripod.motorPos['119']) > max_yaw_step) or (long(self.tripod.motorPos['119']) < -max_yaw_step):

            logging.info("Limite del giunto 119 superato, {} < {} < {}".format(
                -max_step, self.tripod.motorPos['119'], max_step))

        else:

            # Uso la cinematica per determinare gli angoli dalle posizioni dei giunti
            result = self.tripod.kinematic.find_solution_fast(
                [
                    -float(self.tripod.motorPos['120']) / self.tripod.kinematic.mt_to_step,
                    -float(self.tripod.motorPos['121']) / self.tripod.kinematic.mt_to_step,
                    -float(self.tripod.motorPos['122']) / self.tripod.kinematic.mt_to_step,
                    float(self.tripod.motorPos['119']) / self.tripod.kinematic.radians_to_step
                ]
            )

            # Catturo gli angoli
            if result:

                roll = self.tripod.kinematic.zyx3
                pitch = self.tripod.kinematic.zyx2
                yaw = self.tripod.kinematic.zyx1

                # TODO: Qui dovrei convertire la terna
                if self.tripod.posTime > 0:
                    v_roll = (roll - self.tripod.old_roll) / self.tripod.posTime / 1000
                    v_pitch = (pitch - self.tripod.old_pitch) / self.tripod.posTime / 1000
                    v_yaw = (yaw - self.tripod.old_yaw) / self.tripod.posTime / 1000
                    self.tripod.old_roll = roll
                    self.tripod.old_pitch = pitch
                    self.tripod.old_yaw = yaw

            # Se sono in simulazione, salvo il dato nel log
            if self.tripod.canStatus == '8':

                self.tripod.last_sim_time += float(self.tripod.posTime) / 1000.0
                self.tripod.last_sim_file.write(
                    "{};{};{};{};{};{};{};{};{}          \n".format(
                        int(self.tripod.mex_counter),
                        self.tripod.last_sim_time,
                        roll,
                        pitch,
                        yaw,
                        float(self.tripod.motorPos['119']),
                        float(self.tripod.motorPos['120']),
                        float(self.tripod.motorPos['121']),
                        float(self.tripod.motorPos['122'])
                    )
                )

        try:

            # R12.321;P-2.231;Y0.000;VR12.12;VP0.00;VY0.00;AS0;T10;C0
            self.transport.write(
                "R{:+07.3f};P{:+07.3f};Y{:+08.3f};RS{:+07.2f};PS{:+07.2f};YS{:+07.2f};AS{};T{:04.1f};C{:03d}\n".format(
                    roll,
                    pitch,
                    yaw,
                    v_roll,
                    v_pitch,
                    v_yaw,
                    self.tripod.canStatus,
                    float(self.tripod.posTime),
                    int(self.tripod.OpProgress)
                )
            )

        except:

            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Impossibile inviare lo stato (%s)" % sys.exc_info()[0])
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
