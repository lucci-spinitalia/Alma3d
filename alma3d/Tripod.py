# -*- coding: utf-8 -*-

from twisted.internet import reactor, task
from Config import Config
from Alarm import Alarm
from Canopen import Canopen
from Kinematic import Kinematic
import os
import re
import traceback
import sys
from time import sleep
import stat
import logging


class Tripod():
    """Classe principale per la gestione del tripode.

    Per la gestione del tripode, sono necessarie tre distinte attivita':

      - Abilitazione dei segnali visivi e acustici in base allo stato
      - Esecuzione del programma canopen_server per la comunicazione con i motori
      - Avvio del server TCP per la comunicazione con il programma di controllo remoto

    Il controllo dei segnali visivi ed acustici avviene tramite bus i2c, mentre il loro
    stato dipende da quanto comunicato tramite PIPE dal canopen_server.

    Il dialogo con il programma di controllo dei motori avviene tramite stdin, stdout e PIPE.

    """

    def __init__(self):

        logging.info("Initializing ALMA_Tripod class")

        # Istanzio le classi
        self.config = Config()
        self.canopen = Canopen(self)
        self.alarm = Alarm(self)
        self.kinematic = Kinematic(self)

        self.almaPositionProtocol = None

        self.last_sim = ""
        self.last_sim_file = None
        self.last_sim_time = 0.0

        # All'avvio il sistema si trova nello stato 3, ATTIVO
        self.canStatus = '3'
        self.oldStatus = 'NOS'    # Forzo il primo update
        self.simHash = ''

        self.userLoggedIn = False
        self.isAsyncError = False

        # Inizializza le strutture
        self.motorsAddress = []
        self.motorPos = {'120': 0L, '121': 0L, '122': 0L, '119': 0L}
        self.posTime = 0
        self.OpProgress = 0
        self.isCentered = False
        self.isImporting = False
        self.currentLine = 0
        self.mex_counter = 0L
        self.posTime = 0
        self.almaControlProtocol = None
        self.isReading = False

        self.antenna_weight = 50

        # Indirizzi dei motori
        self.motor_address_list = ['119', '120', '121', '122']

        # Compila i cercatori
        self.find_motor_position = re.compile('@M([^ ]*) S([^ ]*) @M([^ ]*) S([^ ]*) @M([^ ]*) S([^ ]*) @M([^ ]*) S([^ ]*) AS([^ ]*) T([^ ]*) C([^ ]*)')

        # Per prima cosa aggiorno lo stato
        self.update_output()

    def cleanup(self):

        logging.info("De-Initializing ALMA_Tripod class")

        # Invia CT6, spegnimento
        reactor.callFromThread(self.canopen.sendCommand, 'CT6')

        # Chiude lo streamer
        if 'almaPositionProtocol' in vars():
            if self.almaPositionProtocol.posSender:
                self.almaPositionProtocol.posSender.stop()

        # Chiude lo stream_reader
        if 'receiver_thread' in vars():
            self.receiver_thread.stop()

        # Chiude il processo di comunicazione con i motori se attivo
        if self.canopen:
            self.canopen.transport.closeStdin()

        # Chiude il reattore se attivo
        if reactor.running:
            logging.info("Stopping reactor")
            reactor.stop()

        # Solo per rimuovere l'interrupt sul GPIO
        self.alarm.cleanup()

    def start_canopen(self):

        # Avvio il server CANOPEN
        # usePTY serve ad evitare l'ECHO
        # INFO: uso stdbuf per evitare il buffering dell'output se non in terminale
        if self.config.isFake:
            reactor.spawnProcess(self.canopen, "/usr/bin/stdbuf", args=["stdbuf", "--output=L", "--input=0",
                "{}alma3d_canopenshell".format(self.config.INSTALL_PATH),
                "fake",
                "load#libcanfestival_can_socket.so,0,1M,8"], env=os.environ, usePTY=False)
        else:
            reactor.spawnProcess(self.canopen, "/usr/bin/stdbuf", args=["stdbuf", "--output=L", "--input=0",
                "{}alma3d_canopenshell".format(self.config.INSTALL_PATH),
                "load#libcanfestival_can_socket.so,0,1M,8"], env=os.environ, usePTY=False)

    def update_import_progress(self, value, line_num):

        self.OpProgress = value
        self.currentLine = line_num

    def update_import_end(self, md5sum):

        self.isImporting = False
        self.last_sim = md5sum

    def stream_reader(self):

        # TODO: Deve ripartire automaticamente in caso di errore ed in caso di assenza di pipe!
        logging.info("Position reader thread started!")

        isPipeOpen = False

        motorPos = {'120': 0L, '121': 0L, '122': 0L, '119': 0L}
        isAsyncError = False
        canStatus = 3
        isCentered = False
        OpProgress = 0
        mex_counter = 0L
        posTime = 0

        while self.isReading:
            if isPipeOpen:
                try:
                    line = pipein.readline()[:-1]
                    # print 'Parent %d got "%s" at %s' % (os.getpid(), line, time.time( ))
                    # line: @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS4 T9 C0
                    canopen_status = self.find_motor_position.search(line)
                    if canopen_status:
                        motorPos[canopen_status.group(1)] = canopen_status.group(2)
                        motorPos[canopen_status.group(3)] = canopen_status.group(4)
                        motorPos[canopen_status.group(5)] = canopen_status.group(6)
                        motorPos[canopen_status.group(7)] = canopen_status.group(8)
                        # Se lo stato e' zero, vuol dire che c'e' una segnalazione pendente
                        if canopen_status.group(9) == '0' and isAsyncError is False:
                            isAsyncError = True
                        elif canopen_status.group(9) != '0':
                            canStatus = canopen_status.group(9)
                            if not isCentered:
                                if canStatus == '6':
                                    isCentered = True
                        posTime = canopen_status.group(10)
                        OpProgress = canopen_status.group(11)
                        mex_counter = mex_counter + 1

                    reactor.callFromThread(self.update_var_from_canopen, motorPos, isAsyncError, canStatus, isCentered, posTime, OpProgress, mex_counter)

                except Exception, e:
                    # Potrebbe essere semplicemente non disponibile un dato!
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logging.error("Disabling Alarm, device not found! (%s)" % str(e))
                    traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)

                    isFileOpen = False
                    logging.info("Pipe closed!")

            else:
                try:
                    mode = os.stat(self.config.POS_PIPE).st_mode
                    if stat.S_ISFIFO(mode):
                        pipein = open(self.config.POS_PIPE, 'r')
                        isPipeOpen = True
                        continue
                    sleep(0.5)
                except:
                    pass

    def update_var_from_canopen(self, motorPos, isAsyncError, canStatus, isCentered, posTime, OpProgress, mex_counter):

        self.motorPos = motorPos
        self.isAsyncError = isAsyncError
        self.canStatus = canStatus
        self.isCentered = isCentered
        self.posTime = posTime
        if not self.isImporting:
            self.OpProgress = OpProgress
        self.update_output()
        if self.almaPositionProtocol is not None:
            self.mex_counter = mex_counter
            self.almaPositionProtocol.sendPosition()

    def goto_em2(self):

        reactor.callFromThread(self.canopen.sendCommand, 'EM2', "local")

    def send_tcp_response(self, data):

        try:
            self.almaControlProtocol.sendResponse(data)

            # Se e' stato ricevuto l'ok sullo spegnimento, spengo il reattore
            #if data[:7] == "OK CT6":

        except:
            pass

    def traslate_status(self, status):

        if status == '0':
            return 'ERRORE'
        elif status == '1':
            return 'SPENTO'
        elif status == '2':
            return 'EMERGENZA'
        elif status == '3':
            return 'ATTIVO'
        elif status == '4':
            return 'INIZIALIZZATO'
        elif status == '5':
            return 'RICERCA_CENTRO'
        elif status == '6':
            return 'CENTRATO'
        elif status == '7':
            return 'ANALIZZATO'
        elif status == '8':
            return 'SIMULAZIONE'
        elif status == '9':
            return 'FERMO'
        elif status == 'A':
            return 'CENTRAGGIO'
        elif status == 'B':
            return 'RILASCIATO'
        elif status == 'C':
            return 'NON_AUTENTICATO'

    def update_output(self):
        """Aggiorna le uscite in base al nuovo stato
        Sono presenti due stati, quello del server e quello della classe. Normalmente coincidono,
        ma in alcune condizioni divergono ( can='ERRORE', class=stato_in_cui_si_verifica ).
        Questa funzione viene chiamata se e solo se lo stato del sever CANOpen e' cambiato."""

        # Gli stati avanzano in baso allo stream del canopen_server, ad eccezione di NON_AUTENTICATO
        # e ANALIZZATO

        # In base al nuovo stato eseguo delle operazioni
        # Verde: Acceso
        # Giallo: Movimento reale o potenziale
        # Rosso: Errore
        # Beep: Movimento reale
        # Green: Attivo
        #                    Verde  Giallo  Rosso  Buzzer  Recinto  Torque
        # 0 - Errore           I       I      I       I       I       I     I = Invariato
        # 1 - SPENTO           -       -      -       -       -       G     G = Gravita'
        # 2 - EMERGENZA        X       -      X       -       -       T     T = Tenuta
        # 3 - ATTIVO           X       X      -       -       -       T     X = On
        # 4 - INIZIALIZZATO    X       -      -       -       X       T     0 = Libero
        # 5 - RICERCA_CENTRO   X       X      -       X       X       T
        # 6 - CENTRATO         X       X      -       -       X       T
        # 7 - ANALIZZATO       X       X      -       -       X       T
        # 8 - SIMULAZIONE      X       X      -       X       X       T
        # 9 - FERMO            X       X      -       -       X       T
        # A - CENTRAGGIO       X       X      -       X       X       T
        # B - RILASCIATO       X       -      X       X       -       0     * Il recinto si disattiva da quando via TCP compare EM1
        # C - NON_AUTENTICATO  X       X      -       -       X       T

        # Thread safe!
        if self.oldStatus != self.canStatus:
            if self.canStatus == 'C':    # NON_AUTENTICATO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '4':  # INIZIALIZZATO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '5':  # RICERCA_CENTRO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.beep_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '6':  # CENTRATO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '7':  # ANALIZZATO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '8':  # SIMULAZIONE
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.beep_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == '9':  # FERMO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == 'A':  # CENTRAGGIO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.yellow_on()
                self.alarm.beep_on()
                self.alarm.fence_enabled()
                self.alarm.update()
            elif self.canStatus == 'B':  # RILASCIATO
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.red_on()
                self.alarm.beep_on()
                self.alarm.update()
            elif self.canStatus == '1':  # SPENTO
                self.alarm.all_off()
                self.alarm.update()
            elif self.canStatus == '2':  # EMERGENZA
                self.alarm.all_off()
                self.alarm.green_on()
                self.alarm.red_on()
                self.alarm.beep_on()
                self.alarm.update()
            else:
                assert True, "update_output(): Stato %s sconosciuto" % self.canStatus

            # Stampo l'evento
            if len(self.motorPos) > 0:
                motor_yaw = self.motorPos['119']
                motor_front = self.motorPos['120']
                motor_rear_right = self.motorPos['121']
                motor_rear_left = self.motorPos['122']
            else:
                motor_yaw = 0
                motor_front = 0
                motor_rear_right = 0
                motor_rear_left = 0

            logging.info("Position: (%s, %s, %s, %s), Status: %s (%s), Time: %s, Completed: %s" % (
                motor_yaw,
                motor_front,
                motor_rear_right,
                motor_rear_left,
                self.traslate_status(self.canStatus),
                self.canStatus,
                self.posTime, self.OpProgress))

            self.oldStatus = self.canStatus