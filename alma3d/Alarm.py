# -*- coding: utf-8 -*-

# Importazioni globali
import RPi.GPIO as GPIO
import smbus
import sys
import traceback
import logging

# Importazioni di package
from Config import Config


class Alarm():
    """Gestione della sirena di allarme
    Questa classe consente la gestione della sirena di allarme che viene controllata tramite bus I2C e la 
    scheda pi-relay della seed-studio nr. 103030029.
    """
    
    def __init__(self, tripod):

        logging.info("Initializing ALMA_Alarm class")

        # Per riportare allarmi al programma
        self.tripod = tripod
    
        # Carico il file di configurazione
        self.config = Config()

        # Inizializzo le variabili        
        self.buzzer = False
        self.green = True
        self.yellow = False
        self.red = False
        self.INPUT_PIN = self.config.FENCE_PIN   # Seleziona il pin 12
        self.isFencePresent = False
        self.isFenceEnabled = True
        self.isFencedCrossed = False

        # Allarme ottico/acustico
        try:
            self.rele_bus = smbus.SMBus(1)  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
            self.DEVICE_ADDRESS = 0x20      # 7 bit address (will be left shifted to add the read write bit)
            self.DEVICE_REG_MODE1 = 0x06
            self.DEVICE_REG_DATA = 0xff
        except IOError:
            logging.info("No alarm/buzzer found!")
            self.isAlarmPresent = False            

        # Imposta l'allarme
        self.search_alarm()

        # Imposta il pin della barriera ad infrarossi
        self.search_fence()

        # Stampa lo stato
        self.alarm_status()
        
        # Aggiorno lo stato
        self.update()

    def search_fence(self):
    
        # Arma il recinto
        self.fence_enabled()
    
        try:

            self.isFencePresent = True
            self.isFenceEnabled = False
            GPIO.setmode(GPIO.BCM)                   # Imposta il pin secondo la numerazione BCM
            GPIO.setup(self.INPUT_PIN, GPIO.IN)      # Lo imposta in input
            GPIO.add_event_detect(self.INPUT_PIN, GPIO.BOTH, callback=self.detect_fence_change, bouncetime=10)
            self.detect_fence_change(self.INPUT_PIN)

        except:

            self.isFencePresent = False
            self.isFenceEnabled = True
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
            logging.info("No fence found!")
        
    def search_alarm(self):
    
        try:
        
            self.rele_bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)
            self.isAlarmPresent = True
        
        except:
        
            logging.info("No alarm/buzzer found!")
            self.isAlarmPresent = False
            
    def cleanup(self):
    
        try:
        
            if self.isFencePresent:
                logging.info("Rimuovo l'interrupt sul GPIO")
                GPIO.remove_event_detect(self.INPUT_PIN)
            self.all_off()
            self.update()

        except:
        
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.error("Disabling Alarm, device not found! (%s)" % sys.exc_info()[0])
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
            self.isAlarmPresent = False

    def alarm_status(self):
    
        if self.buzzer:
            status = "Buzzer: On, "
        else:
            status = "Buzzer: Off, "
        if self.red:
            status += "Red: On, "
        else:
            status += "Red: Off, "
        if self.yellow:
            status += "Yellow: On, "
        else:
            status += "Yellow: Off, "
        if self.green:
            status += "Green: On, "
        else:
            status += "Green: Off, "
        if self.isFenceEnabled:
            status += "Fence: On"
        else:
            status += "Fence: Off"
        logging.info(status) 
        # traceback.print_stack()

    def fence_enabled(self):
    
        logging.info("Fence enabled")
        self.isFenceEnabled = True
        self.isFencedCrossed = False
        
    def fence_disabled(self):
    
        logging.info("Fence disabled")
        self.isFenceEnabled = False
        self.isFencedCrossed = False
        self.all_off()
        
    def clear_cross(self):
    
        if self.isFencePresent:
            if self.isFencedCrossed:
               self.isFencedCrossed = False
               self.all_off() 

    def detect_fence_change(self, channel):

        if not self.isFenceEnabled:
            return

        if self.isFencePresent:
            if not GPIO.input(self.INPUT_PIN):
                if not self.isFencedCrossed:
                    self.isFencedCrossed = True
                    self.tripod.goto_em2()

    def beep_on(self):

        self.buzzer = True
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA &= ~(0x1 << 0)
        
    def green_on(self):

        self.green = True
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA &= ~(0x1 << 1)
        
    def yellow_on(self):

        self.yellow = True
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA &= ~(0x1 << 2)
        
    def red_on(self):

        self.red = True
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA &= ~(0x1 << 3)

    def beep_off(self):

        self.buzzer = False
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA |= (0x1 << 0)

    def green_off(self):

        self.green = False
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA |= (0x1 << 1)

    def yellow_off(self):

        self.yellow = False
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA |= (0x1 << 2)

    def red_off(self):

        self.red = False
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA |= (0x1 << 3)

    def all_on(self):

        self.buzzer = True
        self.green = True
        self.yellow = True
        self.red = True
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA &= ~(0xf << 0)

    def all_off(self):

        self.buzzer = False
        self.green = False
        self.yellow = False
        self.red = False
        self.alarm_status()
        if self.isAlarmPresent:
            self.DEVICE_REG_DATA |= (0xf << 0)
            
    def update(self):
    
        if self.isAlarmPresent:
            self.rele_bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)


if __name__ == '__main__':

    from time import sleep

    # Imposto il logging
    # - debug
    #   - info
    #   - warn
    #   - error
    #   - critical
    FORMAT = "[%(filename)s:%(lineno)3s - %(funcName)20s() ] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    class Tripod():

        def __init__(self):

            self.config = Config()
            self.config.isFake = True
            self.motor_address_list = ['119', '120', '121', '122']

        def update_import_progress(self, progress, rownum):

            print "{} / {}".format(progress, rownum)

        def update_import_end(self, md5sum):

            pass

    my_tripod = Tripod()

    # Istanzio la classe
    a = Alarm(my_tripod)
    a.fence_enabled()

    print "Hallo!"

    sleep(10)