# -*- coding: utf-8 -*-

from twisted.internet import reactor
import logging
import time
import subprocess
import threading
import traceback
import sys
import csv
import os
import math
import kinematic_cy
import shutil

M_PI = 3.14159265358979323846
M_TO_RAD = 0.0174532925199432957692

class Kinematic():
    """Implementazione della cinematica diretta del Tripode

    Il tripode e' disposto secondo il seguente schema:

                ^ Y
                .
                .           (2,122)
                .         _,o                                o
                .      _,.  |                 o              |
                .   _,.     |                 |              |
        (1,120) . ,.        |                 |              o
    - - - - - - o - - - - - | - - -> X        |              |
                . '._       |                |-|            |-|
                .    '._    |                | |            | |
                .       '._ |                | |<-. (Alpha) | |
                .          'o                | |   '.       | |
                .           (3,121)          |_|    v       |_|
                .                             O---------+----o

    Il tripode, per come è stato costruito, funziona con la terna di Tait-Bryan Z1Y2X3:

                     |  c1c2    c1s2s3 - c3s1    s1s3 + c1c3s2  |
            Z1Y2X3 = |  c2s1    c1c3 + s1s2s3    c3s1s2 - c1s3  |
                     |  -s2         c2s3             c2c3       |

    La convenzione avionica è invece la Y1X2Z3, ovvero:

                     |  c1c3 + s1s2s3    c3s1s2 - c1s3    c2s1  |
            Y1X2Z3 = |      c2s3              c2c3        -s2   |
                     |  c1s2s3 - c3s1    c1c3s2 + s1s3    c1c2  |

    Dal momento che gli angoli vengono definiti dalla sequenza scelta di operazioni, e che il roll è in pratica
    la rotazione attorno all'asse X SE E SOLO SE la sequenza di rotazioni è x1y2z3, ho deciso di nominame gli
    angoli come r1_xyz, da non confondere con r1_zyx.

    Per caricare il file di simulazione, e per inviare le posizioni, sono utilizzate due
    funzioni di conversione che passano da una notazione all'altra.

    Attenzione! A seconda della terna selezionata, l'angolo 1 è diverso dall'angolo 1 di
    un'altra terna.

    Qualche nota sulla convenzione avionica; gli assi sono orientati con la mano destra,
    il 1 X in avanti, il 2 Y verso destra, il 3 Z verso il basso.

    Gli angoli sono orientati con la regola della mano destra, in roll o rollio la rotazione
    rispetto al primo asse (X), il pitch o beccheggio attorno al secondo asse (Y), lo yaw o
    l'imbardata attorno l'asse Z.

    L'ordine di rotazioni in avionica sia Yaw, Pitch, Roll, quindi RzRyRx, ovvero XYZ.

    Se l'ordine di rotazione risulta Roll->Pitch->Yaw (Rx*Ry*Rz)

        Rx: rotation about X-axis, roll
        Ry: rotation about Y-axis, pitch
        Rz: rotation about Z-axis, yaw(heading)

            pitch         roll         yaw
             Ry            Rx          Rz
         | Cy  0 Sy|   |1  0   0|   |Cz -Sz 0|   | CyCz + SySxSz    -CySz + SxSyCz    SyCx |
         |  0  1  0| * |0 Cx -Sx| * |Sz  Cz 0| = |     CxSz              CxCz         -Sx  |
         |-Sy  0 Cy|   |0 Sx  Cx|   | 0   0 1|   | -SyCz + CySxSz   SySz + CySxCz     CyCx |

    """

    # Inizializzo il sistema
    # Angoli in gradi per le definizioni
    # Angoli in radianti nei calcoli
    #   Distanze in metri

    vmax = 40               # Massima velocita' angolare in gradi/sec
    amax = 40               # Massima accellerazione angolare in gradi/sec^2

    alpha_limit = 10        # Massima escursione dei pistoni in +/- 10 gradi

    base_radius = 0.705     # Raggio dei centri dei tre pistoni
    real_height = 1.685     # Distanza tre i centri cerniera-sfera sullo 0 ( 400mm )

    ke = 150                # Guadagno nella ricerca dell'angolo
    err_limit = 0.00015     # Errore sotto il quale la soluzione si considera esatta ( 0,1mm )
    cycle_limit = 3000      # Numero massimo di interazioni

    step_per_turn = 8000    # Numero di step in un giro motore
    mt_per_turn = 0.01      # Metri per giro motore
    rot_reduction = 115  # Rapporto del riduttore del giunto rotazionale

    max_lin_speed = 400     # Velocita' lineare massima in mm/s (40gradi/s su pitch e roll -> 585861 step/s -> 732)
    max_rot_speed = 40      # Velocita' angolare massima in gradi/s

    def __init__(self, tripod=None):

        kinematic_cy.init()

        self.tripod = tripod

        # Calcolo le costanti in radianti
        self.vmax_r = self.vmax * M_TO_RAD
        self.amax_r = self.amax * M_TO_RAD
        self.alpha_limit_r = -self.alpha_limit * M_TO_RAD

        # Calcolo i fattori di conversione dei motori
        self.mt_to_step = self.step_per_turn / self.mt_per_turn
        self.radians_to_step = self.step_per_turn * self.rot_reduction / (2 * M_PI)

        # Calcola le velocita' massime
        self.max_lin_step_per_s = ((self.max_lin_speed / 1000.0) / self.mt_per_turn) * self.step_per_turn * 1.2
        self.max_rot_step_per_s = (self.max_rot_speed * M_TO_RAD) * self.radians_to_step * 1.2

        # Inizializzo le posizioni delle basi dei pistoni
        self.base_length = self.base_radius * math.sqrt(3)
        self.base_height = 3 * self.base_radius / 2
        self.base_point = [[0, 0, 0],
                           [self.base_height, self.base_length / 2, self.base_length / 2],
                           [self.base_height, -self.base_length / 2, -self.base_length / 2]]

        # Inizializzo le posizioni dei centri sfera del triangolo superiore
        self.roof_vertex_x = [0.0, 0.0, 0.0]
        self.roof_vertex_y = [0.0, 0.0, 0.0]
        self.roof_vertex_z = [0.0, 0.0, 0.0]

        # Memorizza i vecchi angoli per avviare da questi la successiva ricerca
        self.isLastAnglesValid = False

        # Angoli tra la base ed i pistoni
        self.alpha = [0.0, 0.0, 0.0]
        self.alpha_start = []
        self.temp = []

        # Numero di cicli eseguiti
        self.cycles = 0

        # Output del risolutore
        self.rx_zyx = 0.0
        self.ry_zyx = 0.0
        self.rz_zyx = 0.0
        self.rx_zyx_r = 0.0
        self.ry_zyx_r = 0.0
        self.rz_zyx_r = 0.0
        self.rx_yxz = 0.0
        self.ry_yxz = 0.0
        self.rz_yxz = 0.0
        self.rx_yxz_r = 0.0
        self.ry_yxz_r = 0.0
        self.rz_yxz_r = 0.0

        # Calcolo della cinematica inversa
        self.icycles = 0
        self.ierr0 = 0.0
        self.ierr1 = 0.0
        self.ierr2 = 0.0

        # Log
        # logging.debug("Tripod parameters")
        # logging.debug("       Base length: %s" % self.base_length)
        # logging.debug("       Base height: %s" % self.base_height)
        # logging.debug("        Base point:  %s" % self.base_point)
        # logging.debug("       Zero height: %s" % self.real_height)
        self.parser_thread = None
        self.sim_file = ""
        self.tcp_protocol = None

        # Conversione RPY <-> Coordinate motori
        self.last_conversion_steps = [0, 0, 0, 0]
        self.last_conversion_positions = [0, 0, 0, 0]

    def distance_12(self, alphas, motor_positions):
        """Calcolo della distanta tra i centri sfera dei pistoni 1 e 2

        In ingresso vengono forniti i tre angoli ipotetici, e le tre altezze dei pistoni

        """

        self.roof_vertex_z[0] = motor_positions[0] * math.cos(alphas[0])
        self.roof_vertex_x[0] = motor_positions[0] * math.sin(alphas[0])
        self.roof_vertex_z[1] = motor_positions[1] * math.cos(alphas[1])
        s2 = motor_positions[1] * math.sin(alphas[1])
        self.roof_vertex_x[1] = self.base_point[1][0] - (s2 * 0.5)                   # sin 30° = 1/2
        self.roof_vertex_y[1] = self.base_point[1][1] - (s2 * 0.8660254037844386)  # cos 30° = sqrt(3) / 2

        return math.sqrt(
            ((self.roof_vertex_x[1] - self.roof_vertex_x[0]) ** 2) +
            (self.roof_vertex_y[1] ** 2) +
            ((self.roof_vertex_z[1] - self.roof_vertex_z[0]) ** 2))

    def distance_23(self, alphas, motor_positions):
        """Calcolo della distanta tra i centri sfera dei pistoni 2 e 3

        In ingresso vengono forniti i tre angoli ipotetici, e le tre altezze dei pistoni

        """

        self.roof_vertex_z[1] = motor_positions[1] * math.cos(alphas[1])
        # s2 = motor_positions[1] * math.sin(alphas[1])
        # self.roof_vertex_x[1] = self.base_point[1][0] - (s2 * 0.5)                 # sin 30° = 1/2
        # self.roof_vertex_y[1] = self.base_point[1][1] - (s2 * 0.8660254037844386)  # cos 30° = sqrt(3) / 2

        self.roof_vertex_z[2] = motor_positions[2] * math.cos(alphas[2])
        s3 = motor_positions[2] * math.sin(alphas[2])
        self.roof_vertex_x[2] = self.base_point[2][0] - (s3 * 0.5)                 # sin 30° = 1/2
        self.roof_vertex_y[2] = self.base_point[2][1] + (s3 * 0.8660254037844386)  # cos 30° = sqrt(3) / 2

        return math.sqrt(
            ((self.roof_vertex_x[2] - self.roof_vertex_x[1]) ** 2) +
            ((self.roof_vertex_y[1] - self.roof_vertex_y[2]) ** 2) +
            ((self.roof_vertex_z[2] - self.roof_vertex_z[1]) ** 2))

    def distance_13(self, alphas, motor_positions):
        """Calcolo della distanta tra i centri sfera dei pistoni 1 e 3

        In ingresso vengono forniti i tre angoli ipotetici, e le tre altezze dei pistoni

        """

        self.roof_vertex_z[0] = motor_positions[0] * math.cos(alphas[0])
        self.roof_vertex_x[0] = motor_positions[0] * math.sin(alphas[0])
        self.roof_vertex_z[2] = motor_positions[2] * math.cos(alphas[2])

        #s3 = motor_positions[2] * math.sin(alphas[2])
        #self.roof_vertex_x[2] = self.base_point[2][0] - (s3 / 2)  # sin 30° = 1/2
        #self.roof_vertex_y[2] = self.base_point[2][1] + (s3 * 0.8660254037844386)  # cos 30° = sqrt(3) / 2

        return math.sqrt(
            ((self.roof_vertex_x[2] - self.roof_vertex_x[0]) ** 2) +
            (self.roof_vertex_y[2] ** 2) +
            ((self.roof_vertex_z[2] - self.roof_vertex_z[0]) ** 2))

    def next_iteration(self, alpha, step_alpha, i, j, n, err):

        self.cycles += 1
        logging.debug("Cycle: {:4d} ({:4d}, {:4d}, {:4d}) "
                      "/ Alpha: ({:+0.6f}, {:+0.6f}, {:+0.6f}) "
                      "/ Step: ({:+0.6f}, {:+0.6f}, {:+0.6f}) "
                      "/ Err: ({:+0.6f}, {:+0.6f}, {:+0.6f})".format(
                          self.cycles,
                          i,
                          j,
                          n,
                          alpha[0],
                          alpha[1],
                          alpha[2],
                          step_alpha[0],
                          step_alpha[1],
                          step_alpha[2],
                          err[0],
                          err[1],
                          err[2])
                      )

    def search_base_angles(self, motor_positions):
        """Calcola la cinematica diretta del tripode

        Partendo dalle altezze degli attuatori, ricava l'inclinazione del piano

        motor_positions:
            - 0: motore 120, posizione in metri di altezza dalla colonna anteriore
            - 1: motore 121, posizione in metri di altezza dalla colonna posteriore sinistra
            - 2: motore 122, posizione in metri di altezza dalla colonna posteriore destra
            - 3: motore 119, posizione in radianti del giunto rotativo

        """

        # Errore nelle soluzioni
        err = [0, 0, 0]

        # Angolo di inizio ricerca
        # Se gia' eseguita una conversione suo i valori precedenti
        if self.isLastAnglesValid:
            self.alpha_start = list(self.alpha)
        else:
            # Angolo minimo di partenza ( -alpha_limit )
            # TO_CHECK: perche' parto da una configurazione sicuramente errata? -10?
            self.alpha_start = [self.alpha_limit_r, self.alpha_limit_r, self.alpha_limit_r]

        # Angoli presunti
        # self.temp = list(self.alpha_start)
        alpha = list(self.alpha_start)

        # Altezze reali degli attuatori
        height = [self.real_height + motor_positions[0],
                  self.real_height + motor_positions[1],
                  self.real_height + motor_positions[2]]

        # Trovo il mediano tra 0-1-2
        '''
        if any([all([motor_positions[0] > motor_positions[1], motor_positions[0] < motor_positions[2]]),
                all([motor_positions[0] < motor_positions[1], motor_positions[0] > motor_positions[2]])]):
            is_0_median = True
            is_1_median = False
            is_2_median = False
        else:
            is_0_median = False
            if any([all([motor_positions[1] > motor_positions[2], motor_positions[1] < motor_positions[0]]),
                    all([motor_positions[1] < motor_positions[2], motor_positions[1] > motor_positions[0]])]):
                is_0_median = False
                is_1_median = True
                is_2_median = False
            else:
                is_1_median = False
                if any([all([motor_positions[2] > motor_positions[1], motor_positions[2] < motor_positions[0]]),
                        all([motor_positions[2] < motor_positions[1], motor_positions[2] > motor_positions[0]])]):
                    is_0_median = False
                    is_1_median = False
                    is_2_median = True
                else:
                    is_2_median = False
        '''

        # Incrementi degli angoli
        # TO_CHECK: perche' quattro? L'ultimo e' di backup?
        step_alpha_base = 0.1 * M_TO_RAD
        step_alpha = [step_alpha_base, step_alpha_base, step_alpha_base]

        # Numero di cicli eseguiti
        self.cycles = 0
        n = 0

        # Calcolo la condizione iniziale
        d1 = self.distance_12(alpha, height)
        err[0] = d1 - self.base_length
        step_alpha[1] = err[0] * self.ke * step_alpha_base

        d2 = self.distance_23(alpha, height)
        err[1] = d2 - self.base_length
        step_alpha[2] = err[1] * self.ke * step_alpha_base

        d3 = self.distance_13(alpha, height)
        err[2] = d3 - self.base_length
        step_alpha[0] = err[2] * self.ke * step_alpha_base

        # Ciclo per la variazione di alfa1
        #for i in range(self.cycle_limit):
        i = 0
        while i < self.cycle_limit:

            i += 1

            # Incremento alfa1 ed azzero alfa2
            #if is_0_median:
            #    alpha[0] -= step_alpha[0]
            #else:
            alpha[0] += step_alpha[0]
            alpha[1] = self.alpha_start[1]

            j = 0

            while j < self.cycle_limit:

                j += 1

                #self.next_iteration(alpha, step_alpha, i, j, n, err)
                self.cycles += 1

                if self.cycles > self.cycle_limit:
                    logging.error("Maximum number of cycles executed, no solution found!")
                    return False

                # Incremento alfa1 ed azzero alfa2
                #if is_1_median:
                #    alpha[1] -= step_alpha[1]
                #else:
                alpha[1] += step_alpha[1]


                # Se supero l'angolo limite
                # Partendo da -10 ( -0.17 ), non devo superare 10 ( 0.17 )
                if alpha[1] > -self.alpha_limit_r:

                    # Angolo non trovato
                    step_alpha[1] = step_alpha_base
                    step_alpha[0] = err[0] * step_alpha_base * self.ke
                    self.alpha_start[1] = -self.alpha_limit_r - 2 * step_alpha[1]
                    break

                d1 = self.distance_12(alpha, height)
                err[0] = d1 - self.base_length
                step_alpha[1] = err[0] * self.ke * step_alpha_base

                if abs(err[0]) < self.err_limit:

                    # Trovato il minimo
                    self.alpha_start[1] = alpha[1]
                    step_alpha[1] = step_alpha_base

                    n = 0
                    while n < self.cycle_limit:

                        n += 1

                        #self.next_iteration(alpha, step_alpha, i, j, n, err)
                        self.cycles += 1

                        if self.cycles > self.cycle_limit:
                            logging.error("Maximum number of cycles executed, no solution found!")
                            return False

                        #if is_2_median:
                        #    alpha[2] -= step_alpha[2]
                        #else:
                        alpha[2] += step_alpha[2]
                        d2 = self.distance_23(alpha, height)
                        err[1] = d2 - self.base_length
                        step_alpha[2] = err[1] * self.ke * step_alpha_base

                        if abs(err[1]) < self.err_limit:

                            step_alpha[2] = step_alpha_base
                            d3 = self.distance_13(alpha, height)
                            err[2] = d3 - self.base_length
                            step_alpha[0] = err[2] * self.ke * step_alpha_base

                            if abs(err[2]) < self.err_limit:

                                # Trovatas la soluzione
                                self.alpha = list(alpha)
                                #print self.cycles
                                return True

                            # NEXT j!!!
                            break

                    # Next i!!!
                    break

    def find_plane_angles(self, roof_motor_position):
        """Determina gli angoli di un piano passante per tre punti

        https://en.wikipedia.org/wiki/Euler_angles#Tait.E2.80.93Bryan_angles
        http://www.songho.ca/opengl/gl_anglestoaxes.html
        https://en.wikipedia.org/wiki/Aircraft_principal_axes
        https://www.princeton.edu/~naomi/lecture3.pdf

        Usiamo le matrici di rotazione Z1Y2X3, ovvero prima rotazione

                     |  c1c2  c1s2s3 - c3s1  s1s3 + c1c3s2  |
            Z1Y2X3 = |  c2s1  c1c3 + s1s2s3  c3s1s2 - c1s3  |
                     |  -s2       c2s3          c2c3        |
        """

        # Calcolo il punto mediano tra i vertici 2 e 3
        pc_x = (self.roof_vertex_x[1] + self.roof_vertex_x[2]) / 2
        pc_y = (self.roof_vertex_y[1] + self.roof_vertex_y[2]) / 2
        pc_z = (self.roof_vertex_z[1] + self.roof_vertex_z[2]) / 2

        # Questa non so cosa sia
        base_r = [[self.roof_vertex_x[0] - pc_x, self.roof_vertex_y[0] - pc_y, self.roof_vertex_z[0] - pc_z],
                  [self.roof_vertex_x[1] - pc_x, self.roof_vertex_y[1] - pc_y, self.roof_vertex_z[1] - pc_z],
                  [0.0, 0.0, 0.0]]

        # Questa e' la costruzione di una matrice
        mat_rot = [[0.0, 0.0, 0.0],
                   [0.0, 0.0, 0.0],
                   [0.0, 0.0, 0.0]]

        # Non so quale operazione è implementata, ma a me servono solo tre elementi, j=2, i=0,1, j=1, i=0
        # Primo elemento, j=1, i=0
        mr = math.sqrt((base_r[0][0] ** 2) + (base_r[0][1] ** 2) + (base_r[0][2] ** 2))
        mat_rot[1][0] = base_r[0][1] / mr
        # Secondo elemento, j=2, i=0
        mat_rot[2][0] = base_r[0][2] / mr
        # Terzo elemento, j=2, i=1
        mr = math.sqrt((base_r[1][0] ** 2) + (base_r[1][1] ** 2) + (base_r[1][2] ** 2))
        mat_rot[2][1] = base_r[1][2] / mr

        # In alternativa posso calcolare tutti gli elementi della matrice
        # for i in range(2):
        #    mr = math.sqrt((base_r[i][0] ** 2) + (base_r[i][1] ** 2) + (base_r[i][2] ** 2))
        #    for j in range(3):
        #        base_r[i][j] /= mr
        #        mat_rot[j][i] = base_r[i][j]

        # Sono elementi della matrice non utilizzati
        # base_r[2][0] = +base_r[1][1] * base_r[0][2] - base_r[0][1] * base_r[1][2]
        # base_r[2][1] = -base_r[1][0] * base_r[0][2] + base_r[0][0] * base_r[1][2]
        # base_r[2][2] = +base_r[1][0] * base_r[0][1] - base_r[0][0] * base_r[1][1]
        # for i in range(3):
        #    mat_rot[i][2] = base_r[2][i]

        # Qui estraggo la terna di Tait-Bryan angles usata internamente, la Z1Y2X3
        k17 = mat_rot[2][0]
        k16 = mat_rot[1][0]
        l17 = mat_rot[2][1]
        m20 = math.asin(k17)
        i23 = math.cos(m20)
        i24 = k16 / i23
        i25 = l17 / i23
        m19 = math.asin(i24)
        self.rz_zyx_r = m19 + roof_motor_position
        self.ry_zyx_r = math.asin(k17)
        self.rx_zyx_r = math.asin(i25)
        self.rx_zyx = self.rx_zyx_r / M_TO_RAD
        self.ry_zyx = self.ry_zyx_r / M_TO_RAD
        self.rz_zyx = self.rz_zyx_r / M_TO_RAD
        angles = self.angles_to_avionics(self.rx_zyx_r, self.ry_zyx_r, self.rz_zyx_r)
        self.rx_yxz = angles[2]
        self.ry_yxz = angles[0]
        self.rz_yxz = angles[1]
        self.rx_yxz_r = angles[5]
        self.ry_yxz_r = angles[3]
        self.rz_yxz_r = angles[4]

    def angles_to_avionics(self, rx_zyx, ry_zyx, rz_zyx):
        """Converte una terna rotazionale da interna in avionica"""

        # Ora calcolo i termini in funzione degli angoli forniti
        s1c2_yxz = (math.sin(rz_zyx) * math.sin(rx_zyx)) + (math.cos(rz_zyx)* math.sin(ry_zyx) * math.cos(rx_zyx))
        s2_yxz = (math.cos(rz_zyx) * math.sin(rx_zyx)) - (math.sin(rz_zyx) * math.sin(ry_zyx) * math.cos(rx_zyx))
        c2s3_yxz = math.sin(rz_zyx) * math.cos(ry_zyx)

        # Ora trovo gli angoli
        rx_yxz_r = math.asin(s2_yxz)
        c2_yxz = math.cos(rx_yxz_r)
        ry_yxz_r = math.asin(s1c2_yxz / c2_yxz)
        rz_yxz_r = math.asin(c2s3_yxz / c2_yxz)
        rx_yxz = rx_yxz_r / M_PI * 180.0
        ry_yxz = ry_yxz_r / M_PI * 180.0
        rz_yxz = rz_yxz_r / M_PI * 180.0

        return [rx_yxz, ry_yxz, rz_yxz, rx_yxz_r, ry_yxz_r, rz_yxz_r]

    def angles_to_internals(self, rx_yxz, ry_yxz, rz_yxz):
        """Converte una terna rotazionale xyz da avionica ad interna, zyx"""

        # Converto gli angoli in ingresso in gradi
        rx_yxz_r = rx_yxz / 180.0 * M_PI
        ry_yxz_r = ry_yxz / 180.0 * M_PI
        rz_yxz_r = rz_yxz / 180.0 * M_PI

        # Ora calcolo i termini in funzione degli angoli forniti
        c2s3_zyx = (math.cos(ry_yxz_r) * math.sin(rx_yxz_r) * math.cos(rz_yxz_r)) + (math.sin(ry_yxz_r) * math.sin(rz_yxz_r))
        s2_zyx = (math.sin(ry_yxz_r) * math.cos(rz_yxz_r)) - (math.cos(ry_yxz_r) * math.sin(rx_yxz_r) * math.sin(rz_yxz_r))
        s1c2_zyx = math.cos(rx_yxz_r) * math.sin(rz_yxz_r)

        # Ora trovo gli angoli
        ry_zyx_r = math.asin(s2_zyx)
        c2_zyx = math.cos(ry_zyx_r)
        rz_zyx_r = math.asin(s1c2_zyx / c2_zyx)
        rx_zyx_r = math.asin(c2s3_zyx / c2_zyx)
        rx_zyx = rx_zyx_r / M_PI * 180.0
        ry_zyx = ry_zyx_r / M_PI * 180.0
        rz_zyx = rz_zyx_r / M_PI * 180.0

        return [rx_zyx, ry_zyx, rz_zyx, rx_zyx_r, ry_zyx_r, rz_zyx_r]

    def find_solution(self, motor_positions):
        """Determina gli angoli di rx_zyx, ry_zyx e rz_zyx date le altezze dei pistoni relative a 1.685mt"""

        # Valuto il tempo necessario alla trasformazione
        if self.search_base_angles(motor_positions):
            self.find_plane_angles(motor_positions[3])
            # logging.debug("Input: [{:+09.6f}, {:+09.6f}, {:+09.6f}, {:+09.6f}], "
            #              "Position: [{:+06.2f}, {:+06.2f}, {:+06.2f}], "
            #              "Process: {:4d}/{:.3f} ms".format(
            #                  motor_positions[0],
            #                  motor_positions[1],
            #                  motor_positions[2],
            #                  motor_positions[3],
            #                  self.rx_zyx,
            #                  self.ry_zyx,
            #                  self.rz_zyx,
            #                  self.cycles,
            #                  process_time))
            self.isLastAnglesValid = True
            return True
        else:
            self.rz_zyx_r = 0.0
            self.ry_zyx_r = 0.0
            self.rx_zyx_r = 0.0
            self.rx_zyx = 0.0
            self.ry_zyx = 0.0
            self.rz_zyx = 0.0
            self.isLastAnglesValid = False
            return False

    def find_solution_fast(self, motor_positions):

        res = kinematic_cy.search_angles(motor_positions)
        if res[0] == 0:
            self.rx_zyx = res[1]
            self.ry_zyx = res[2]
            self.rz_zyx = res[3]
            self.rx_zyx_r = res[4]
            self.ry_zyx_r = res[5]
            self.rz_zyx_r = res[6]
            self.cycles = res[7]
            angles = self.angles_to_avionics(self.rx_zyx_r, self.ry_zyx_r, self.rz_zyx_r)
            #angles1 = self.angles_to_avionics(self.rx_zyx_r, self.ry_zyx_r, self.rz_zyx_r)
            self.rx_yxz = angles[2]
            self.ry_yxz = angles[0]
            self.rz_yxz = angles[1]
            self.rx_yxz_r = angles[5]
            self.ry_yxz_r = angles[3]
            self.rz_yxz_r = angles[4]
            return True
        else:
            logging.error("Maximum number of cycles executed, no solution found [{}, {}, {} -> {} cycles]!".format(
                motor_positions[0],
                motor_positions[1],
                motor_positions[2],
                motor_positions[3],
                res[7]
            ))
            self.rx_zyx = 0.0
            self.ry_zyx = 0.0
            self.rz_zyx = 0.0
            self.rx_zyx_r = 0.0
            self.ry_zyx_r = 0.0
            self.rz_zyx_r = 0.0
            self.cycles = 0.0
            return False

    def calc_ik(self, rx_zyx, ry_zyx, rz_zyx):
        """Prende gli angoli in ingresso e restituisce la posizione degli attuatori necessaria a raggiungerli.

        La posizione viene definita in step, ed è una lista così organizzata:

        motor_positions:
            - 0: motore 120, posizione in metri di altezza dalla colonna anteriore
            - 1: motore 121, posizione in metri di altezza dalla colonna posteriore sinistra
            - 2: motore 122, posizione in metri di altezza dalla colonna posteriore destra
            - 3: motore 119, posizione in radianti del giunto rotativo
        """

        # Conto i cicli spesi
        cycles_used = 0

        # Costruisco due array
        motor_positions = [0.0, 0.0, 0.0, 0.0]

        # Converto gli angoli richiesti in radianti e me li memorizzo
        angles_r = list([rx_zyx * M_TO_RAD, ry_zyx * M_TO_RAD, rz_zyx * M_TO_RAD])
        angles_r_search = list(angles_r)

        # logging.warn("Required [{:+9.6f}, {:+9.6f}, {:+9.6f}]".format(
        #    angles_r[0],
        #    angles_r[1],
        #    angles_r[2])
        # )

        # Inizializzo l'errore
        err = [0.0, 0.0, 0.0]

        search_limit = 0.0001 / 180.0 * M_PI
        cycle_limit = 100

        # Tre iterazioni sono sufficienti a portare l'errore sotto il millessimo di mm
        for i in range(0, cycle_limit):

            # Calcolo prima due termini costanti
            # dd1 =
            dd1 = self.base_height * math.sin(angles_r_search[1])
            d23 = self.base_length * math.sin(angles_r_search[0])

            # Poi tramite una funzione chiusa ma approssimata determino le altezze richieste
            motor_positions[0] = dd1 / 2
            motor_positions[2] = -dd1 - 0.5 * d23 + motor_positions[0]
            motor_positions[1] = motor_positions[2] + d23
            motor_positions[3] = angles_r_search[2]

            # Uso le altezze per calcolarmi, usando la dk, i valori reali che otterrei
            self.find_solution_fast(motor_positions)
            cycles_used += self.cycles

            # Calcolo l'errore tra gli angoli desiderati, e quelli ottenuti dalla dk
            err[0] = angles_r[0] - self.rx_zyx_r
            err[1] = angles_r[1] - self.ry_zyx_r
            err[2] = angles_r[2] - self.rz_zyx_r

            if math.fabs(err[0]) < search_limit:
                if math.fabs(err[1]) < search_limit:
                    if math.fabs(err[2]) < search_limit:
                        break

            # Uso tali errori per correggere gli angoli in ingresso fino ad ottenere i corretti azionamenti
            angles_r_search[0] += err[0]
            angles_r_search[1] += err[1]
            angles_r_search[2] += err[2]

            # logging.info("Stimulus [{:+9.6f}, {:+9.6f}, {:+9.6f}], "
            #           "Obtained [{:+9.6f}, {:+9.6f}, {:+9.6f}], "
            #           "Error [{:+9.6f}, {:+9.6f}, {:+9.6f}]".format(
            #               angles_r_search[0],
            #               angles_r_search[1],
            #               angles_r_search[2],
            #               self.dk.rx_zyx_r,
            #               self.dk.ry_zyx_r,
            #               self.dk.rz_zyx_r,
            #               N.degrees(err[0]),
            #               N.degrees(err[1]),
            #               N.degrees(err[2])
            #           )
            # )

        self.cycles = cycles_used
        self.icycles = i
        self.ierr0 = err[0]
        self.ierr1 = err[1]
        self.ierr2 = err[2]
        if i == cycle_limit:
            logging.error("Massimo numero di cicli raggiunto ({}, {} ,{})!".format(rx_zyx, ry_zyx, rz_zyx))
            return False
        self.last_conversion_positions = list(motor_positions)
        return True

    def start_parsing(self, md5sum_of_file, tcp_protocol=None):

        # Informa il padre se necessario
        if self.tripod is not None:
            self.tripod.isImporting = True

        # Salvo l'identificativo del file
        self.sim_file = md5sum_of_file

        # Salvo il trasmettitore per inviare eventuali errori
        self.tcp_protocol = tcp_protocol

        # Avvia il thread di importazione
        self.parser_thread = threading.Thread(target=self.sim_parser)
        self.parser_thread.setDaemon(True)
        self.parser_thread.start()

    def convert_point(self, rx_zyx, ry_zyx, rz_zyx):
        """
        Le posizioni dei motori restituite dalla cinematica inversa (motor_positions) sono:

            - 0: motore 120, posizione in metri di altezza dalla colonna anteriore
            - 1: motore 121, posizione in metri di altezza dalla colonna posteriore sinistra
            - 2: motore 122, posizione in metri di altezza dalla colonna posteriore destra
            - 3: motore 119, posizione in radianti del giunto rotativo

        :param rx_zyx:
        :param ry_zyx:
        :param rz_zyx:
        :return:
        """

        motor_steps = [0, 0, 0, 0]

        angles2 = self.angles_to_internals(
            float(rx_zyx.replace(',', '.')), float(ry_zyx.replace(',', '.')), float(rz_zyx.replace(',', '.'))
        )

        if not self.calc_ik(float(angles2[0]), float(angles2[1]), float(angles2[2])):
            return False

        # Converto gli angoli e le altezze dei pistoni in step motore
        motor_steps[0] = int(self.last_conversion_positions[0] * self.mt_to_step)
        motor_steps[1] = int(self.last_conversion_positions[1] * self.mt_to_step)
        motor_steps[2] = int(self.last_conversion_positions[2] * self.mt_to_step)
        motor_steps[3] = int(self.last_conversion_positions[3] * self.radians_to_step)

        # Contrx_zyxo che la posizione assoluta non ecceda i limiti fisici
        if motor_steps[0] < -319999:
            self.format_pos_limit_err_single("inferiore", "120", motor_steps)
            return False
        if motor_steps[0] > 319999:
            self.format_pos_limit_err_single("superiore", "120", motor_steps)
            return False
        if motor_steps[1] < -319999:
            self.format_pos_limit_err_single("inferiore", "121", motor_steps)
            return False
        if motor_steps[1] > 319999:
            self.format_pos_limit_err_single("superiore", "121", motor_steps)
            return False
        if motor_steps[2] < -319999:
            self.format_pos_limit_err_single("inferiore", "122", motor_steps)
            return False
        if motor_steps[2] > 319999:
            self.format_pos_limit_err_single("superiore", "122", motor_steps)
            return False

        # Sembra che l'oscillazione dell'interpretazione angolare sia terminata...
        motor_steps[3] = "{:.0f}".format(-motor_steps[3])
        motor_steps[0] = "{:.0f}".format(-motor_steps[0])
        motor_steps[1] = "{:.0f}".format(-motor_steps[1])
        motor_steps[2] = "{:.0f}".format(-motor_steps[2])

        self.last_conversion_steps = list(motor_steps)
        return True

    def sim_parser(self):
        """Legge il file della simulazione, e per ogni riga Roll, Pitch e Yaw salva una riga nei file motore.

        Il file deve essere scritto nella forma:

        <roll>;<ry_zyx>;<rz_zyx>;<time_to_reach_in_ms>;<optional comment>
        12.321;-2.23;0.001;200;commento opzionale
        12.321;-2.23;0.012;3210.3;

        Per ogni linea:
           - Ignoro i commenti e prendo i campi
           - Con RPY trovo le posizioni dei motori
           - Aggiungo il rumore bianco +/- 1 step
           - Controllo che i valori di step siano compresi tra +/- 320000 per M120-M122
           - Controllo che le velocitÃ  in step/s siano compatibili
           - Scrivo ogni valore di step trovato in un file 119-122.mot nel formato
             CT1 M119 S-1421774321 T18546

        Le posizioni dei motori restituite dalla cinematica inversa (motor_positions) sono:

            - 0: motore 120, posizione in metri di altezza dalla colonna anteriore
            - 1: motore 121, posizione in metri di altezza dalla colonna posteriore sinistra
            - 2: motore 122, posizione in metri di altezza dalla colonna posteriore destra
            - 3: motore 119, posizione in radianti del giunto rotativo

        """

        # Se non esiste la directory la crea
        if not os.path.exists(self.tripod.config.MOT_DATA):
            os.umask(0)
            os.makedirs(self.tripod.config.MOT_DATA, 0777)
        if not os.path.exists(self.tripod.config.LOG_PATH):
            os.umask(0)
            os.makedirs(self.tripod.config.LOG_PATH, 0777)
        if not os.path.exists(self.tripod.config.SIM_PATH):
            os.umask(0)
            os.makedirs(self.tripod.config.SIM_PATH, 0777)

        if len(self.sim_file) < 36:
            logging.error("No valid checksum given, should be 33 bytes lenght")
            # TODO, esci e segnala

        md5_sum_file = self.sim_file.rstrip().upper()[4:]
        logging.info("Analizzo il file {}".format(md5_sum_file))

        found_something = False
        filename = ''

        for file_found in os.listdir(self.tripod.config.SIM_PATH):

            filename = self.tripod.config.SIM_PATH + file_found

            if all([os.path.isfile(filename), filename[-3:] == "csv"]):

                try:
                    md5sum_output = subprocess.check_output([self.tripod.config.MD5SUM_EXEC, filename]).upper()
                except Exception, e:
                    logging.warn("Unable to md5sum file {}".format(filename))
                    continue

                md5sum_output = md5sum_output.split(' ')
                logging.warn("Check file %s: '%s'" % (filename, md5sum_output[0]))
                if md5sum_output[0] == md5_sum_file:
                    logging.warn("Found file {}!".format(file))
                    shutil.copyfile(filename, "{}simulazione_{}.csv".format(self.tripod.config.LOG_PATH, md5_sum_file))
                    found_something = True
                    break

        try:

            if found_something:

                rownum = 0
                motor_file = dict()
                motor_steps = [0L, 0L, 0L, 0L]
                motor_steps_old = [0L, 0L, 0L, 0L]
                zero_suppression = [1, 1, 1, 1]
                old_progress = -1

                f = open(filename, 'rb')
                reader = csv.reader(f, delimiter=';')
                lines = sum(1 for col in reader)
                f.seek(0)

                for col in reader:

                    if rownum == 0:

                        # La prima riga e' un'intestazione
                        # Intanto apro i files di output
                        for motor in self.tripod.motor_address_list:
                            file_name = '{}{}{}'.format(self.tripod.config.MOT_DATA, motor, self.tripod.config.MOT_EXT)
                            logging.warn("File {} opened".format(file_name))
                            motor_file[motor] = open(file_name, "w+")
                            os.chmod(file_name, 0666)
                        log_conversione = open("{}conversione_angoli_step_{}.csv".format(self.tripod.config.LOG_PATH, md5_sum_file), "w+")
                        log_conversione.write("Line;Time;Roll;Pitch;Yaw;Step_119_IK;Step_120_IK;Step_121_IK;Step_122_IK\n")
                        time_log = 0.0

                    else:

                        # Calcolo la posizione dei motori tramite la cinematica diretta
                        sim_roll = float(col[0].replace(',', '.'))
                        sim_pitch = float(col[1].replace(',', '.'))
                        sim_yaw = float(col[2].replace(',', '.'))

                        # Questa e' la terna avionica, quindi devo prima convertirla
                        # NON FUNZIONA LA CONVERSIONE IN CYTHON
                        # angles1 = kinematic_cy.angles_to_internals(sim_roll, sim_pitch, sim_yaw)
                        angles2 = self.angles_to_internals(sim_roll, sim_pitch, sim_yaw)
                        # logging.debug("({}, {}, {}) -> ({}, {}, {}) ({}, {}, {})".format(
                        #    sim_roll,
                        #    sim_pitch,
                        #    sim_yaw,
                        #    angles1[0],
                        #    angles1[1],
                        #    angles1[2],
                        #    angles2[0],
                        #    angles2[1],
                        #    angles2[2]
                        # ))

                        if not self.calc_ik(angles2[0], angles2[1], angles2[2]):
                            # TODO: devo stampare l'errore
                            return False

                        # Converto gli angoli in step motore
                        motor_steps[0] = int(self.last_conversion_positions[0] * self.mt_to_step)
                        motor_steps[1] = int(self.last_conversion_positions[1] * self.mt_to_step)
                        motor_steps[2] = int(self.last_conversion_positions[2] * self.mt_to_step)
                        motor_steps[3] = int(self.last_conversion_positions[3] * self.radians_to_step)

                        # Controllo che la posizione assoluta non ecceda i limiti fisici
                        if motor_steps[0] < -319999:
                            self.format_pos_limit_err("inferiore", "120", rownum, col, motor_steps)
                            return False
                        if motor_steps[0] > 319999:
                            self.format_pos_limit_err("superiore", "120", rownum, col, motor_steps)
                            return False
                        if motor_steps[1] < -319999:
                            self.format_pos_limit_err("inferiore", "121", rownum, col, motor_steps)
                            return False
                        if motor_steps[1] > 319999:
                            self.format_pos_limit_err("superiore", "121", rownum, col, motor_steps)
                            return False
                        if motor_steps[2] < -319999:
                            self.format_pos_limit_err("inferiore", "122", rownum, col, motor_steps)
                            return False
                        if motor_steps[2] > 319999:
                            self.format_pos_limit_err("superiore", "122", rownum, col, motor_steps)
                            return False

                        # Controllo che la velocita' raggiunta dagli attuatori non ecceda i limiti
                        if (abs(motor_steps[0] - motor_steps_old[0]) / (int(col[3]) / 1000.0)) > self.max_lin_step_per_s:
                            self.format_speed_limit_err("120", rownum, col, motor_steps, motor_steps_old)
                            return False
                        if (abs(motor_steps[1] - motor_steps_old[1]) / (int(col[3]) / 1000.0)) > self.max_lin_step_per_s:
                            self.format_speed_limit_err("121", rownum, col, motor_steps, motor_steps_old)
                            return False
                        if (abs(motor_steps[2] - motor_steps_old[2]) / (int(col[3]) / 1000.0)) > self.max_lin_step_per_s:
                            self.format_speed_limit_err("122", rownum, col, motor_steps, motor_steps_old)
                            return False
                        if (abs(motor_steps[3] - motor_steps_old[3]) / (int(col[3]) / 1000.0)) > self.max_rot_step_per_s:
                            self.format_speed_limit_err("119", rownum, col, motor_steps, motor_steps_old)
                            return False

                        #motor_steps_before = list(motor_steps)

                        # Se due campioni sono uguali, la prima volta aggiunge 1 step, la seconda lo toglie
                        if motor_steps[0] == motor_steps_old[0]:
                            motor_steps[0] += zero_suppression[0]
                            zero_suppression[0] = -zero_suppression[0]
                        if motor_steps[1] == motor_steps_old[1]:
                            motor_steps[1] += zero_suppression[1]
                            zero_suppression[1] = -zero_suppression[1]
                        if motor_steps[2] == motor_steps_old[2]:
                            motor_steps[2] += zero_suppression[2]
                            zero_suppression[2] = -zero_suppression[2]
                        if motor_steps[3] == motor_steps_old[3]:
                            motor_steps[3] += zero_suppression[3]
                            zero_suppression[3] = -zero_suppression[3]

                        # logging.warn("{:06d},{:02d}: RPY[{:6.3f}, {:6.3f}, {:6.3f}] STEP[{:+07d}({:+07d}), {:+07d}({:+07d}), {:+07d}({:+07d}), {:+07d}({:+07d})] - SPEED[{:6.0f}, {:6.0f}, {:6.0f}, {:6.0f}]".format(
                        #    rownum,
                        #    int(col[3]),
                        #    float(col[0].replace(',', '.')),
                        #    float(col[1].replace(',', '.')),
                        #    float(col[2].replace(',', '.')),
                        #    motor_steps[0],
                        #    motor_steps_before[0],
                        #    motor_steps[1],
                        #    motor_steps_before[1],
                        #    motor_steps[2],
                        #    motor_steps_before[2],
                        #    motor_steps[3],
                        #    motor_steps_before[3],
                        #    abs((motor_steps[0] - motor_steps_old[0]) * 1000.0) / int(col[3]),
                        #    abs((motor_steps[1] - motor_steps_old[1]) * 1000.0) / int(col[3]),
                        #    abs((motor_steps[2] - motor_steps_old[2]) * 1000.0) / int(col[3]),
                        #    abs((motor_steps[3] - motor_steps_old[3]) * 1000.0) / int(col[3]))
                        # )

                        # Salvo i vecchi valori
                        motor_steps_old = list(motor_steps)

                        # --------------------------------------------------------------------------------------------
                        # Stampare la percentuale
                        # --------------------------------------------------------------------------------------------
                        motor_file['119'].write("CT1 M119 S{:.0f} T{}\n".format(-motor_steps[3], col[3]))
                        motor_file['120'].write("CT1 M120 S{:.0f} T{}\n".format(-motor_steps[0], col[3]))
                        motor_file['121'].write("CT1 M121 S{:.0f} T{}\n".format(-motor_steps[1], col[3]))
                        motor_file['122'].write("CT1 M122 S{:.0f} T{}\n".format(-motor_steps[2], col[3]))
                        time_log += float(col[3]) / 1000.0
                        log_conversione.write("{};{};{};{};{};{};{};{};{}\n".format(
                            rownum,
                            time_log,
                            sim_roll,
                            sim_pitch,
                            sim_yaw,
                            motor_steps[3],
                            motor_steps[0],
                            motor_steps[1],
                            motor_steps[2]))
                    rownum += 1
                    progress = int(rownum * 100.0 / lines)
                    if old_progress != progress:
                        if reactor:
                            reactor.callFromThread(self.tripod.update_import_progress, progress, rownum)
                        else:
                            #print "{:04d} with {:4d} cycles, [{:7.3f}, {:7.3f}, {:7.3f}] -> [{:7.0f}, {:7.0f}, {:7.0f}, {:7.0f}]".format(
                            #    rownum,
                            #    self.cycles,
                            #    roll_sim,
                            #    pitch_sim,
                            #    yaw_sim,
                            #    motor_step[0],
                            #    motor_step[1],
                            #    motor_step[2],
                            #    motor_step[3])
                            pass
                        old_progress = progress

                for motor in self.tripod.motor_address_list:
                    logging.warn("File {} closed".format(motor))
                    motor_file[motor].close()
                log_conversione.close()

                print "Data loaded, {} lines".format(lines)
                if self.tcp_protocol is not None:
                    self.tcp_protocol.sendLine('OK CT3')
                if reactor:
                    reactor.callFromThread(self.tripod.update_import_end, md5_sum_file)
                return True

            else:

                if self.tcp_protocol is not None:
                    self.tcp_protocol.sendLine('CERR CT3 0: File not found')

            if reactor:
                reactor.callFromThread(self.tripod.update_import_end, "")
            return False

        except csv.Error as e:

            if self.tcp_protocol is not None:
                self.tcp_protocol.sendLine("CERR CT3 1: CSV parser error, file %s, line %d, content '%s': %s" % (filename, rownum, str(col), e))
            logging.error("CSV parser error, file %s, line %d: %s" % (filename, reader.line_num, e))
            if reactor:
                reactor.callFromThread(self.tripod.update_import_end, "")
            return False

        except Exception, e:

            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Error on parsing file! (%s)" % sys.exc_info()[0])
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
            if self.tcp_protocol is not None:
                self.tcp_protocol.sendLine("CERR CT3 1: CSV parser error, file %s, line %d, content '%s': %s" % (filename, reader.line_num, str(col), e))
            if reactor:
                reactor.callFromThread(self.tripod.update_import_end, "")
            return False

    def format_pos_limit_err(self, direction, motor, rownum, col, motor_step):

        if self.tcp_protocol is not None:
            self.tcp_protocol.sendLine('ERR CT3 0: Limite {} raggiunto nel giunto {} alla linea {}:{}'.format(
                direction, motor, rownum, col))
        if direction == "inferiore":
            edir = "lower"
        else:
            edir = "upper"
        logging.error('ERR CT3 0: Motor {} {} limit reached on line {}:{} ({}, {}, {}, {})'.format(
            motor, edir, rownum, col, motor_step[0], motor_step[1], motor_step[2], motor_step[3]))
        if reactor:
            reactor.callFromThread(self.tripod.update_import_end, "")

    def format_pos_limit_err_single(self, direction, motor, motor_step):

        if self.tcp_protocol is not None:
            self.tcp_protocol.sendLine('ERR CT1 0: Limite {} raggiunto nel giunto {}'.format(
                direction, motor))
        if direction == "inferiore":
            edir = "lower"
        else:
            edir = "upper"
        logging.error('ERR CT1 0: Motor {} {} limit reached ({}, {}, {}, {})'.format(
            motor, edir, motor_step[0], motor_step[1], motor_step[2], motor_step[3]))

    def format_speed_limit_err(self, motor, rownum, col, motor_step, motor_step_old):
        if self.tcp_protocol is not None:
            self.tcp_protocol.sendLine('ERR CT3 0: Velocità limite raggiunta nel giunto {} alla linea {}:{}'.format(
                motor, rownum, col))
        logging.error('ERR CT3 0: Motor {} speed limit reached on line {}:{} ({}, {}, {}, {})-({}, {}, {}, {})'.format(
            motor, rownum, col, motor_step[0], motor_step[1], motor_step[2], motor_step[3], motor_step_old[0],
            motor_step_old[1], motor_step_old[2], motor_step_old[3]))
        if reactor:
            reactor.callFromThread(self.tripod.update_import_end, "")


def test_distance(k):

    # Provo le funzioni di calcolo delle distanze
    alphas = [0.3, 0.4, 0]
    motor_positions = [k.base_height + 0.2, k.base_height + 0.1, k.base_height - 0.2]
    distance_12 = k.distance_12(alphas, motor_positions)
    distance_23 = k.distance_23(alphas, motor_positions)
    distance_13 = k.distance_13(alphas, motor_positions)
    # 0.52804341498, 0.885684986893, 0.980524171149
    if (distance_12 - 0.528043414) > 0.000000001:
        print "Assert: distance_12() errata, {} != {}".format(distance_12, 0.52804341498)
        return
    if (distance_23 - 0.885684986) > 0.000000001:
        print "Assert: distance_23() errata, {} != {}".format(distance_12, 0.885684986893)
        return
    if (distance_13 - 0.980524171) > 0.000000001:
        print "Assert: distance_13() errata, {} != {}".format(distance_12, 0.980524171149)
        return
    print "test_distance: OK ({:011.9f}, {:011.9f}, {:011.9f})".format(distance_12, distance_23, distance_13)


def test_dk(k):

    # Ecco alcuni punti da provare
    #                        1        2        3              R       P       Y
    list_pos = [[+0.0000, +0.0533, -0.0533, 0.000],
                [+0.0000, +0.1060, -0.1060, 0.000],
                [+0.0461, -0.0461, -0.0461, 0.000],
                [+0.0919, -0.0919, -0.0919, 0.000],
                [+0.0461, +0.0069, -0.0991, 0.000],
                [+0.0918, +0.0125, -0.1960, 0.000],
                [+0.0000, +0.0533, -0.0533, 1.586],
                [+0.0000, +0.1060, -0.1060, 1.586],
                [+0.0461, -0.0461, -0.0461, 1.586],
                [+0.0919, -0.0919, -0.0919, 1.586],
                [+0.0461, +0.0069, -0.0991, 1.586],
                [+0.0918, +0.0125, -0.1960, 1.586]]

                # 57248;+020035;-049659;-007453;+107733;-006.82;-006.78;+0007.44;AS8;T09;C015;004 / 003.57 ms
                # 57249;+020320;-050393;-007552;+109293;-006.92;-006.88;+0007.53;AS8;T09;C015;007 / 003.59 ms
                # 57250;+020890;-051858;-007736;+112414;-007.02;-006.98;+0007.64;AS8;T09;C015;036 / 009.64 ms

    for pos in list_pos:
        k.find_solution(pos)  # [ +05.00, +00.00, +000.00]
        print "[{:+07.4f}, {:+07.4f}, {:+07.4f}, {:+07.4f}] ->  [{:+08.4f}, {:+08.4f}, {:+09.4f}]".format(
            pos[0],
            pos[1],
            pos[2],
            pos[3],
            k.roll,
            k.pitch,
            k.yaw)


def test_speed():

    pos = [+0.0000, +0.0532, -0.0532, 0.000]
    iterations = 500
    step = 0.5
    k.find_solution(pos)
    cycles = k.cycles
    start = time.time()
    for i in range(iterations):
        pos[2] += step
        pos[3] -= step
        k.find_solution(pos)
        cycles = (cycles + k.cycles) / 2
        if step == 0.5:
            step = -0.5
        else:
            step = 0.5
    total_time = ((time.time() - start) / iterations) * 1000000
    print "Pure python implementation {:06.2f} us / cycle, {} cycles in {:04.2f}ms".format(total_time / cycles, cycles, total_time / 1000.0)


def test_speed_fast():

    pos = [+0.0000, +0.0532, -0.0532, 0.000]
    iterations = 500
    step = 0.5
    k.find_solution_fast(pos)
    cycles = k.cycles
    start = time.time()
    for i in range(iterations):
        pos[2] += step
        pos[3] -= step
        k.find_solution_fast(pos)
        cycles = (cycles + k.cycles) / 2
        if step == 0.5:
            step = -0.5
        else:
            step = 0.5
    total_time = ((time.time() - start) / iterations) * 1000000
    print "Pure cython implementation {:06.2f} us / cycle, {} cycles in {:04.2f}ms".format(total_time / cycles, cycles, total_time / 1000.0)


def test_pitch_problem():

    sin_step = 1000
    sin_ampl = 40

    my_yaw = 0.0
    motor_steps = [0L, 0L, 0L, 0L]

    log_conversion = open("{}/conversion_{}.csv".format(my_tripod.config.LOG_PATH, my_tripod.last_sim_file), "w+")
    log_henry.write("Count;ERoll;EPitch;EYaw;Roll;Pitch;Yaw;Step_119;Step_120;Step_121;Step_121;CRoll;CPitch;CYaw;"
                    "ICycles;Err0;Err1;Err2;DCycles\n")

    for i in range(sin_step):
        my_roll = sin_ampl * 0.5 * math.sin(2 * M_PI * (i + 100) / 500)
        my_pitch = sin_ampl * math.sin(2 * M_PI * i / 500)
        if not k.calc_ik(my_roll, my_pitch, my_yaw):
            return
        motor_steps[0] = int(self.last_conversion_positions[0] * k.mt_to_step)
        motor_steps[1] = int(self.last_conversion_positions[1] * k.mt_to_step)
        motor_steps[2] = int(self.last_conversion_positions[2] * k.mt_to_step)
        motor_steps[3] = int(self.last_conversion_positions[3] * k.radians_to_step)
        my_cycles = k.cycles
        k.find_solution_fast(motor_positions)
        log_henry.write("{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{}\n".format(
            i,
            str(my_roll - k.roll).replace(".", ","),
            str(my_pitch - k.pitch).replace(".", ","),
            str(my_yaw - k.yaw).replace(".", ","),
            str(my_roll).replace(".", ","),
            str(my_pitch).replace(".", ","),
            str(my_yaw).replace(".", ","),
            motor_steps[3],
            motor_steps[0],
            motor_steps[1],
            motor_steps[2],
            str(k.roll).replace(".", ","),
            str(k.pitch).replace(".", ","),
            str(k.yaw).replace(".", ","),
            k.icycles,
            k.ierr0,
            k.ierr1,
            k.ierr2,
            my_cycles,
            )
        )


    log_henry.close()

def test_conversion(k):

    #                      ZYX                            -> YXZ
    list_pos = [[0.1750, -0.1750, 0.1750, -43.2093, 23.3041, -3.8373, -36.7647, 25.5449, -4.4003]]

    for pos in list_pos:

        k.find_solution_fast([-float(pos[0]), -float(pos[1]), -float(pos[2]), 0])
        dcyc = k.cycles

        m = k.calc_ik(k.rx_zyx, k.ry_zyx, k.rz_zyx)
        icyc = k.cycles
        logging.debug(
            "({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                pos[0], pos[1], pos[2], 0,
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )
        m = k.calc_ik(k.rx_zyx, k.rz_zyx, k.ry_zyx)
        icyc = k.cycles
        logging.debug(
            "                                  -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )

        m = k.calc_ik(k.rz_zyx, k.rx_zyx, k.ry_zyx)
        icyc = k.cycles
        logging.debug(
            "                                  -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )
        m = k.calc_ik(k.rz_zyx, k.ry_zyx, k.rx_zyx)
        icyc = k.cycles
        logging.debug(
            "                                  -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )

        m = k.calc_ik(k.ry_zyx, k.rz_zyx, k.rx_zyx)
        icyc = k.cycles
        logging.debug(
            "                                  -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )
        m = k.calc_ik(k.ry_zyx, k.rx_zyx, k.rz_zyx)
        icyc = k.cycles
        logging.debug(
            "                                  -> ({:07.4f}, {:07.4f}, {:07.4f}) {:04d} -> ({:06.4f}, {:06.4f}, {:06.4f}, {:06.4f}) {:04d}".format(
                k.rx_zyx, k.ry_zyx, k.rz_zyx, dcyc,
                k.last_conversion_positions[0], k.last_conversion_positions[1], k.last_conversion_positions[2], k.last_conversion_positions[3], icyc
            )
        )

        """logging.debug(
            "({}, {}, {}) -> ({:07.4f}({:07.4f}), {:07.4f}({:07.4f}), {:07.4f}({:07.4f}) -> "
            "({:07.4f}({:07.4f}), {:07.4f}({:07.4f}), {:07.4f}({:07.4f}))".format(
                pos[0], pos[1], pos[2],
                k.rx_zyx, pos[3],
                k.ry_zyx, pos[4],
                k.rz_zyx, pos[5],
                k.rx_yxz, pos[6],
                k.ry_yxz, pos[7],
                k.rz_yxz, pos[8]
            )
        )"""

if __name__ == '__main__':

    # Solo per attivare il debug remoto
    # pydevd.settrace('192.168.178.106', port=10010, stdoutToServer=True, stderrToServer=True)

    # Imposto il logging
    # - debug
    #   - info
    #   - warn
    #   - error
    #   - critical
    FORMAT = "[%(filename)s:%(lineno)3s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    # Per eseguire i test
    import alma3d.Config

    class Tripod():

        def __init__(self):

            self.config = alma3d.Config.Config()
            self.config.isFake = True
            self.motor_address_list = ['119', '120', '121', '122']

        def update_import_progress(self, progress, rownum):

            print "{} / {}".format(progress, rownum)

        def update_import_end(self, md5sum):

            pass

    reactor = False

    my_tripod = Tripod()

    # Istanzio la classe
    k = Kinematic(my_tripod)

    # Provo le distanze
    #test_distance(k)

    # Provo la corretta risoluzione di alcuni punti noti
    #test_dk(k)

    # Provo la velocita'
    # test_speed()
    # test_speed_fast()

    # Provo la cinematica inversa e trovo la combinazione di angoli che porta alla posizione limite dell'attuatore
    #for i in range(30):
    #    k.calc_ik(i, i, 0.0)
    #    print("{}, {}, {:06d}, {:06d}, {:06d}, {:06d}".format(i,
    #                                                          k.max_lin_step_per_s,
    #                                                          int(k.last_conversion_positions[0] * k.mt_to_step),
    #                                                          int(k.last_conversion_positions[1] * k.mt_to_step),
    #                                                          int(k.last_conversion_positions[2] * k.mt_to_step),
    #                                                          int(k.last_conversion_positions[3] * k.radians_to_step)))
    # Eseguo prove note di posizioni angolari
    # k.calc_ik(0.968, 0.968, 0.000)
    # k.calc_ik(1.013, 1.013, 0.000)
    # k.calc_ik(1.058, 1.058, 0.000)

    # Provo l'importazione di una simulazione
    # start = time.time()
    # k.calc_ik(40.744, 0.0, 0.0)
    #k.start_parsing("CT3 E156E86AC46F5DB4CC563F18AC4825EB")
    #k.parser_thread.join()
    # print "Pure python implementation {:06.2f} ms / simulation".format(((time.time() - start)) * 1000)
    # test_pitch_problem()

    # Roll, Pitch, Yaw
    test_conversion(k)
