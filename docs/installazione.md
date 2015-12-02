
Aggiunto l'utente Spinitalia
============================

Aggiunto l'utente spinitalia, con password RlyxEaLeKXV7n3CC, insertiro tra i
SUDOERS.

Configurato SSH
===============

Disabilitato l'accesso con password da ssh, ed abilitato quello con chiavi.

Cambiate le password di root
============================

Cambiate le password di root, ed elimintati gli altri utenti, per evitare
accessi locali non voluti. Disabilitato getty da init.

Condivisione cartella per salvataggio simulazioni
=================================================

  - Installato samba-server

    sudo apt-get install samba samba-common-bin

  - Aggiunta la directory /home/spinitalia/simulazioni
  - Aggiunta dell'utente spinitalia/spinitalia

  - Nel file /etc/samba/smb.conf:

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
        passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:*
        %n\n *password\supdated\ssuccessfully* .
        pam password change = yes
        map to guest = bad user

        usershare allow guests = no

      [simulazioni]
        comment = Cartella temporanea per le simulazioni
        path = /home/spinitalia/simulazioni
        writable = yes
        create mask = 0600
        directory mask = 0700
        valid user = spinitalia


Automount delle pennette USB con esecuzione del firmware se presente
====================================================================

Avvio automatico del servizio
=============================

Nel file /etc/inittab è stato inserito il comando:

  #3:23:respawn:/usr/bin/screen -D -m python /opt/spinitalia/service/alma3d_service.py

