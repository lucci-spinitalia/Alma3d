# Preparazione di un update

Per preparare un update, occorre eseguire i seguenti comandi:

    '''Bash
     zip -P BSQ9tdXDZlKc alma3d_spinitalia_update *
     mv alma3d_spinitalia_update.zip alma3d_spinitalia_update
    '''

Il contenuto dell'archivio verrà copiato in /opt/spinitalia/, e successivamente verrà eseguito lo script do_update
se presente.

Interventi effettuati prima della partenza

1. Implementazione terna avionica
2. I file di simulazione, ed i log, sono stati messi in una directory temporanea
   Cambiato /lib/init/mount-functions.sh
      # Mount /tmp as tmpfs if enabled.
      if [ yes = "$RAMTMP" ]; then
          domount "$MNTMODE" tmpfs shmfs /tmp tmpfs "-o${NODEV}nosuid$TMP_OPT"
          # Make sure we don't get cleaned
          touch /tmp/.tmpfs
          # Create /tmp/spinitalia/simulation/
          mkdir /tmp/spinitalia
          chmod 0777 /tmp/spinitalia
          mkdir /tmp/spinitalia/simulation
          chmod 0777 /tmp/spinitalia/simulation
          mkdir /tmp/spinitalia/logs
          chmod 0777 /tmp/spinitalia/logs
      else
3. Riconfigurato samba per puntare alla dir temporanea
4. Inserito l'update via USB
   /etc/usbmount/mount.d/01_check_update

      #!/bin/sh

      # Controlla la presenza di un update
      # UM_DEVICE       -> /dev/sda1
      # UM_MOUNTPOINT   -> /media/usb0
      # UM_FILESYSTEM   -> vfat
      # UM_MOUNTOPTIONS -> sync,noexec,nodev,noatime,nodiratime
      # UM_VENDOR       -> SanDisk
      # UM_MODEL        -> Cruzer Edge
      set -e

      V_LOG_OUTPUT="/var/run/usbmount/update_output"

      echo "      UM_DEVICE: $UM_DEVICE"        > $V_LOG_OUTPUT
      echo "  UM_MOUNTPOINT: $UM_MOUNTPOINT"   >> $V_LOG_OUTPUT
      echo "  UM_FILESYSTEM: $UM_FILESYSTEM"   >> $V_LOG_OUTPUT
      echo "UM_MOUNTOPTIONS: $UM_MOUNTOPTIONS" >> $V_LOG_OUTPUT
      echo "      UM_VENDOR: $UM_VENDOR"       >> $V_LOG_OUTPUTst
      echo "       UM_MODEL: $UM_MODEL"        >> $V_LOG_OUTPUT

      if [ "$UM_MOUNTPOINT" = "/media/usb0" ]; then
        if [ -e "${UM_MOUNTPOINT}/alma3d_spinitalia_update" ]; then
           if [ ! -e /opt/spinitalia ]; then
              mkdir /opt/spinitalia
           fi
           unzip -P BSQ9tdXDZlKc ${UM_MOUNTPOINT}/alma3d_spinitalia_update -d /opt/spinitalia
           if [ -e /opt/spinitalia/do_update ]; then
             /opt/spinitalia/do_update
             rm /opt/spinitalia/do_update
           fi
        fi
      fi

      exit 0

   ${UM_MOUNTPOINT}/alma3d_spinitalia_update
   unzip ${UM_MOUNTPOINT}/alma3d_spinitalia_update -P BSQ9tdXDZlKc -d /opt/spinitalia

   zip -P BSQ9tdXDZlKc alma3d_spinitalia_update *

   mv alma3d_spinitalia_update.zip alma3d_spinitalia_update


