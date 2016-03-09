
## Aggiunto l'utente Spinitalia

Aggiunto l'utente spinitalia, con password RlyxEaLeKXV7n3CC, insertiro tra i SUDOERS.

## Configurato SSH

Disabilitato l'accesso con password da ssh, ed abilitato quello con chiavi.

## Cambiate le password di root

Cambiate le password di root, ed elimintati gli altri utenti, per evitare accessi locali non voluti. Disabilitato getty da init.

## Condivisione cartella per salvataggio simulazioni

  - Installato samba-server
    ```
    sudo apt-get install samba samba-common-bin
    ```
  - Aggiunta la directory */tmp/spinitalia/simulation*, mappata con *\\SPINITALIA-ALMA\simulazioni*.
  - Aggiunta la directory */opt/spinitalia/exposed_through_smb*, mappata con *\\SPINITALIA-ALMA\installazione*.
  - Aggiunta dell'utente spinitalia/spinitalia a samba
  - Nel file */etc/samba/smb.conf*:
  
    ```Text
    [global]

      workgroup = SPINITALIA
      server string = "Tripode Spinitalia Alma3D"
      dns proxy = no
    
      log file = /var/log/samba/log.%m
      max log size = 1000
      syslog = 0
      panic action = /usr/share/samba/panic-action %d
    
      encrypt passwords = true
      passdb backend = tdbsam
      obey pam restrictions = yes
      unix password sync = yes
      passwd program = /usr/bin/passwd %u
      passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:* %n\n *password\supdated\ssuccessfully* .
      pam password change = yes
      map to guest = bad user
    
      usershare allow guests = no
    
    [simulazioni]
      comment = Cartella temporanea per le simulazioni tripode Alma3d di Spinitalia S.R.L.
      path = /tmp/spinitalia/simulation
      writable = yes
      create mask = 0666
      directory mask = 0777
      valid users = spinitalia
    
    [installazione]
      comment = Cartella contenente il software utile per usare il tripode Alma3d di Spinitalia S.R.L.
      path=/opt/spinitalia/exposed_through_smb
      writable = none
      valid users = spinitalia
            
    ```


## Automount delle pennette USB con installazione nuovo firmware

  - Ho installato il servizio di mounting automatico delle pennette usb:
  
    ```
    sudo apt-get install samba samba-common-bin
    ```
    
  - Ho creato lo script di aggiornamento */etc/usbmount/mount.d/01_check_update*:
  
    ```Text
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
    echo "      UM_VENDOR: $UM_VENDOR"       >> $V_LOG_OUTPUT
    echo "       UM_MODEL: $UM_MODEL"        >> $V_LOG_OUTPUT
    
    if [ "$UM_MOUNTPOINT" = "/media/usb0" ]; then
      if [ -e "${UM_MOUNTPOINT}/alma3d_spinitalia_update" ]; then
         logger Found an update on usb-pen
         unzip -P BSQ9tdXDZlKc -o ${UM_MOUNTPOINT}/alma3d_spinitalia_update -d /opt/spinitalia
         if [ -e /opt/spinitalia/do_update ]; then
           logger Found an update script on usb-pen
           /opt/spinitalia/do_update
           rm /opt/spinitalia/do_update
         fi
      fi
    fi
    ```

## Preparazione dell'aggiornamento del firmware

  - Bisogna creare un archivio contenente tutti i files da inserire nella path */opt/spinitalia*:
    ```
    cd /opt/spinitalia
    zip -1 -P BSQ9tdXDZlKc -r /tmp/alma3d_spinitalia_update *
    ```
  - Se necessario, può essere inserito all'interno lo script */opt/spinitalia/do_update* che verrà automaticamente eseguito al termine dell'installazione.
  
## Avvio automatico del servizio

Nel file /etc/inittab è stato inserito il comando:

  3:23:respawn:/usr/bin/screen -D -m python /opt/spinitalia/service/alma3d_service.pyc

## Configurazione del sistema

Il firmware è configurabile tramite il file */opt/spinitalia/service/config.ini*:
```
# Definizioni fisiche del sistema
[Dimensions]
base_radius: 0.705     ; Raggio dei centri dei tre pistoni in metri
real_height: 1.685     ; Distanza tre i centri cerniera ed i centri sfera dopo l'homing ( 0.4m ) in metri

# Definizione delle velocita massime
[Speed]
vmax: 40               ; Massima velocita' angolare in gradi/sec
amax: 40               ; Massima accellerazione angolare in gradi/sec^2
max_lin_speed: 400     ; Velocita' lineare massima in mm/s (40gradi/s su pitch e roll -> 585861 step/s -> 732)
max_rot_speed: 40      ; Velocita' angolare massima in gradi/s

# Parametri della cinematica
[Kinematic]
alpha_limit: 10        ; Massima escursione dei pistoni in +/- gradi
ke: 150                ; Guadagno nella ricerca dell'angolo
err_limit: 0.00015     ; Errore sotto il quale la soluzione si considera esatta ( 0,15mm )
cycle_limit: 3000      ; Numero massimo di interazioni

# Parametri dei motori
[Motors]
step_per_turn: 8000    ; Numero di step in un giro motore
mt_per_turn: 0.01      ; Metri per giro motore
rot_reduction: 115     ; Rapporto del riduttore del giunto rotazionale

# Path del sistema
[Path]
base_path: /opt/spinitalia/service/
sim_path: /tmp/spinitalia/simulation/
log_path: /tmp/spinitalia/logs/
position_path: /opt/spinitalia/default_position/
motor_data_path: /tmp/spinitalia/motor_data/
motor_ext_fake: .mot.fake
mot_ext: .mot

# Pipe
[Pipe]
pipe_position_fake: /tmp/fake_alma_3d_spinitalia_pos_stream_pipe
pipe_position: /tmp/alma_3d_spinitalia_pos_stream_pipe

# Configurazione di sistema
[System]
canopen_fake: True
fence_pin: 12
```

In passato, e viene qui riportato solo per riferimento, veniva usato un altro file:
```
# -*- coding: utf-8 -*-

class Config():

    def __init__(self):

        self.isFake = True
        self.isLoginRequired = True
        self.FENCE_PIN = 12
        self.INSTALL_PATH = "/opt/spinitalia/service/"
        self.SIM_PATH = "/tmp/spinitalia/simulation/"
        self.LOG_PATH = "/tmp/spinitalia/logs/"
        #self.SIM_PATH = "/mnt/nas/media/"
        self.DEF_MOVE = "/opt/spinitalia/default_position/"
        self.MOT_DATA = "/tmp/spinitalia/motor_data/"
        self.MD5SUM_EXEC = '/usr/bin/md5sum'
        if self.isFake:
            self.MOT_EXT = ".mot.fake"
        else:
            self.MOT_EXT = ".mot"
        if self.isFake:
            self.POS_PIPE = "/tmp/fake_alma_3d_spinitalia_pos_stream_pipe"
        else:
            self.POS_PIPE = "/tmp/alma_3d_spinitalia_pos_stream_pipe"
```

## Servizi TCP

Risulta necessario rimuovere il servizio dhcpcd5 che erroneamente ignora il file di configurazione ed assegna di sua spontanea volontà un secondo IP al sistema:

```
sudo apt-get remote dhcpcd5
```

Il sistema utilizza le seguenti porte TCP:

  - Porta 10000: Ricerca del tripode tramite Broadcast Multicast su gruppo "228.0.0.5"
  - Porta 10001: Stream in tempo reale con le posizioni, le velocità e lo stato del tripode
  - Porta 10002: Protocollo di controllo del Tripode
  
  
