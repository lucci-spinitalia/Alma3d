#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from alma3d import Kinematic
import alma3d.Kinematic
import pydevd
import logging


class Tripod():

    def __init__(self):

        # Indirizzi dei motori
        self.motor_address_list = ['119', '120', '121', '122']

    def update_import_end(self):

        pass

    def update_import_progress(self):

        pass


if __name__ == '__main__':

    # Classe di utilità per il test
    my_tripod = Tripod()

    # Configuro il logging
    #logging = logging.getLogger('root')
    FORMAT = "[%(filename)s:%(lineno)3s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.WARN)

    # Solo per attivare il debug remoto
    pydevd.settrace('192.168.178.106', port=10010, stdoutToServer=True, stderrToServer=True)

    # Istanzio la classe
    k = alma3d.Kinematic.Kinematic(my_tripod)

    # Eseguo i test
    k.sim_file = "CT3 A16CD216C158E356899B5D834DF1DA1E"
    k.sim_parser()


