=================================[ Manuale interno ]=================================

Rev.9 -- da confrontare con il manuale cliente! --
Data 1/09/2015


Indice
======

  1. Descrizione generale
  2. Ricerca dell'indirizzo del tripode
  3. Invio di una simulazione
  4. Determinazione della posizione del tripode
  5. Operazioni con il tripode
  6. Processi
  7. Funzionalita da implementare
  8. Unittest

  A. Unita' di misura
  B. Stati del sistema
  C. Riferimenti


1. Descrizione generale
=======================

Il tripode Spinitalia Alma3D e' dotato di una connessione Ethernet 10/100
accessibile tramite il connettore RJ45 (CN09) del quadro di comando generale
(QCG).

Una volta connesso alla rete, il tripode si configura con un IP fornito
dal servizio DHCP presente, oppure con un indirizzo IP statico se
configurato.


2. Ricerca dell'indirizzo del tripode
=====================================

Il tripode invia il proprio indirizzo IP rispondendo ad una richiesta
UDP Multicast sul gruppo 228.0.0.5, porta 10000, contenente la stringa
'Ping Spinitalia_ALMA3D'.

La risposta 'Pong Spinitalia_ALMA3D' giungera' via UDP direttamente
dal tripode, consentendone di identificare l'IP.

Un altro metodo per trovare l'ip consiste nel richidere la risoluzione
inversa al server WINS del computer SPINITALIA_ALMA3D.


3. Invio di una simulazione
===========================

Per prima cosa occorre preparare un file in formato csv, con le righe
organizzate cosi:

  <roll>;<pitch>;<yaw>;<time_to_reach_in_ms>;<optional comment>
  12.321;-2.23;0.001;200;commento opzionale
  12.321;-2.23;0.012;3210.3;

E' ignorata automaticamente la prima linea se contiene un'intestazione.

Gli angoli ed il tempo sono espressi secondo la seguente notazione:

  Roll:  -45.00 ... +45.00 gradi
  Pitch: -45.00 ... +45.00 gradi
  Yaw:     0.00 ... 360.00 gradi
  Time:       1 ... 256000  ms

Il tempo si intende come quello necessario a raggiungere la posizione
indicata, e viene espresso in ms, fino ad un massimo di 256000. Vista la
sua funzione, il tempo non puo' essere minore di 1 ms, pena l'esclusione
del comando.

Una volta pronto il file bisogna calcolare l'hash MD5(rif. 1) dello stesso,
tramite ad esempio il programma md5summer (rif. 2). Il nome del file non
riveste particolare importanza, dal momento che il sistema distingue le
simulazioni dall'hash md5.

Per inviare un file della simulazione, basta accedere alla directory
condivisa \\SPINITALIA-ALMA3D\simulazioni e salvarlo al suo interno.


4. Determinazione della posizione del tripode
=============================================

Il programma alma3d_canopenshell apre una pipe all'avvio, che si trova nella
directory /tmp e ha nome fake_alma_3d_spinitalia_pos_stream_pipe se in
funzionamento virtuale oppure alma_3d_spinitalia_pos_stream_pipe se in
funzionamento reale.

Una volta aperta fornisce le seguenti informazioni secondo il seguente
formato:

  @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS6 T9 C0

Le informazioni fornite possiedono la seguente notazione:

  (@M)   Indirizzo motore:           @M119 ... @M122
  (S)    Step del motore:          -320000 ... 320000 (+-2^31)
  (AS)   Alma status: stato del tripode (vedi appendice B)
  (T)    Tempo:                          0 ... 2^32 ms
  (C)    Progresso analisi/simulazione:  0 ... 100%

Il motore viene identificato come @M<indirizzo>, possiede 8000 step in un
giro, ed in ogni giro si eleva di 10mm. Lo zero corrisponde ad un altezza
di 400mm più e l'escurione totale ad 800mm. La distanza centro sfera centro
cerniera dei pistoni e' di 1285mm.

Il sistema trasforma le altezze dei pistoni in angoli R, P e Y.

Connettendosi alla porta 10001 del tripode si puo' ricevere la posizione
dello stesso, che viene trasmessa come un flusso continuo di coordinate in
questa forma:

  R12.321;P-2.23;Y0;AS0;T10;C0;avvio simulazione 33c995835f28604045b1256f645c9195
  R12.321;P-2.23;Y0;AS0;T10;C0

Il tempo, in questo caso, rappresenta i ms intercorsi tra un'informazione e
l'altra. La simulazione viene identificata con l'hash md5. Gli angoli ed il
tempo sono espressi secondo la seguente notazione:

  (R)  Roll:        -45.00 ... +45.00 gradi
  (P)  Pitch:       -45.00 ... +45.00 degree
  (Y)  Yaw:           0.00 ... 360.00 degree
  (AS) Alma status: stato del tripode (vedi appendice B)
  (T)  Time:             0 ... 2^32 ms
  (C)  Progress:         0 ... 100%

Il tempo si intende come quello impiegato a raggiungere la posizione
indicata, e viene espresso in ms.


5. Operazioni con il tripode
============================

Il controllo del Tripode Spinitalia Alma 3d avviene tramite procotollo TCP
sulla porta 10002.

Per le possibili interazioni tra i comandi e gli stati si rimanda alla
figura 1 (tripode.png).

Le seguenti affermazioni circa il protocollo sono sempre valide:

    - I comandi restituiscono se a buon fine:

        OK <cmd>

    - I comandi restituiscono se in errore:

        CERR <cmd> <num>: <descr>

    - Esistono errori non causati dall'esecuzione di un comando. In
      tal caso puo' essere restituito un errore asincrono oltre alla
      risposta normale al comando indicata nei punti precedenti:

        AERR <num>: <descr>

Una volta scoperto l'indirizzo IP, bisogna innanzitutto fornire le
credenziali di accesso al sistema, tramite il comando LGN. A seguito del
riconoscimento dell'utente è possibile interagire inviando gli altri
comandi. La lista completa e' di seguito riportata:

		LGN:   Accesso al sistema
    CT<x>: Avvio della procedura x
    EM<x>: Avvio del comando di emergenza x
    PR<x>: Lettura o scrittura del parametro x

Qui di seguito viene riportato l'elenco completo le procedure implementate:

		- LGN <user> <password>

	        Accede al sistema tramite le credenziali fornite. Il nome utente
          e' fisso, 'alma_user', mentre la password di default e'
          'spinitalia'.
					Per l'accesso come amministratore in caso di manutenzione, basta
          loggarsi come 'alma3d_admin' e password da decidere.

          In caso di successo viene inviata la stringa:

						OK LGN

					In caso di errore:

            CERR LGN 0: Wrong password

    - CT0 M4  Avvia la procedura di inizializzazione dei 4 motori, che
              restituisce la loro lista in ordine libero di risposta,
              secondo il seguente formato:

                @M A121      ( non disponibile all'esterno )
                @M A52       ( non disponibile all'esterno )
                @M A12       ( non disponibile all'esterno )
                @M A43       ( non disponibile all'esterno )
                OK CT0

              se tutti i motori sono presenti, altrimenti:

                CERR CT0 0: Motori dichiarati non trovati

              Devo mandare

                60FB 008 Signed 32 bit
                PR5 M120 O60FB S008 T32s 64F
                PR5 M121 O60FB S008 T32s 64F
                PR5 M122 O60FB S008 T32s 64F

          Imposto a 0Fh il parametro con sub-index 5 dell'oggetto 60FBh
          con un 8bit unsigned ( <8/16/32><s/u> )

    - CT1 M119 P1231232 VM123 AM124 [S]

          Porta il tripode nel punto identificato dalle quattro coordinate in step dei motori, con una
          velocita' di 123 in unita' motore con un'accellerazione di 124 in unita' motore.
          Se il comando termina con S, viene anche inviato lo start a tutti i motori.

          VT = Velocity * 65536      ( Giri al secondo   )
          AT = Acceleration * 8192   ( Giri al secondo^2 )

          Per l'attuatore rotativo, questi valori diventano:

          VT = Velocity * 65536 * 115 / 360     ( Gradi al secondo   )
          AT = Acceleration * 8192 * 115 / 360  ( Gradi al secondo^2 )

          Per l'attuatore lineare, questi valori diventano:

          VT = Velocity * 65536 * 10     ( mm al secondo   )
          AT = Acceleration * 8192 * 10  ( mm al secondo^2 )

    - CT1 M52 S-1421774321 T18546 ( non disponibile all'esterno )

          Muove il motore con indirizzo 52 allo step -1.421.774.321 in
          18,546 secondi. Questo comando viene inserito all'interno del
          file 52.mot e proviene da un file di configurazione non
          accessibile dall'esterno.

    - CT1 M121 H-2314085 VF2000 VB1000  ( non disponibile all'esterno )

          Imposta la posizione di HOME del motore con indirizzo 121 ad
          una distanza di -2.314.085 step dal finecorsa, raggiungendolo
          con una velocita' di 2000RPM ed allontanandosi con una velocita'
          di 1000RPM. Questo comando viene inserito all'interno del file
          121.mot e proviene da un file di configurazione non accessibile
          dall'esterno.

    - CT2 P1

          Avvia la procedura di ricerca il fine corsa di tutti i motori e si
          sposta nella posizione configurata come HOME.

    - CT2 P2

          Sposta il sistema nella posizione di home.

    - CT2 P3

          Porta con gravita' il sistema al minimo di altezza.

    - CT2 P4

          Porta il sistema al minimo di altezza in modo controllato.

    - CT3 5757c1a61f2360039e0cb3c15a1cd69f

          Avvia il controllo della simulazione che deve essere presente nella
          nella cartella condivisa '\\TRIPODEALMA3D\' e generare un HASH
          MD5SUM pari a 5757c1a61f2360039e0cb3c15a1cd69f.

          Se il contenuto del file risulta regolare, il comando restituisce:

            OK CT3

          Durante la conversione, il processo indica la percentuale di
          completamento nello stream della porta 10001.

    - CT4

          Per prima cosa abilito i limiti di giunto per i pistoni per garantire la
          movimentazione completa, ma li lascia disabilitati nel motore di
          rotazione (yaw).

            PR5 M120-122 O2101 S03 T16u 2 # Limite sinistro
            PR5 M120-122 O2101 S03 T16u 3 # Limite destro

          Avvia la simulazione il cui file originario presenta un HASH
          MD5SUM pari a 5757c1a61f2360039e0cb3c15a1cd69f.

          Quando e' terminata, il sistema restituisce:

            OK CT4

          Durante la conversione, il processo indica la percentuale di
          completamento nello stream della porta 10001.

    - CT5

          Arresta la simulazione interrompendola. Questo comando e'
          l'unico ad essere accettato durante una simulazione, e
          provoca le seguenti risposte:

            CERR CT5 0: Simulazione interrotta
            OK CT5

    - CT6

          Spegne il sistema portando il piano in posizione di riposo
          orizzontale alla sua altezza minima. Al termine dell'operazione
          invia:

            OK CT6

          Successivamente esegue l'arresto completo del dispositivo.

Sono implementate le seguenti procedure di emergenza:

    - EM1

          Rilascia tutti i motori. Normalmente restituisce:

            OK EM1

    - EM2

          Blocca tutti i motori ovunque essi siano. Normalmente
          restituisce:

            OK EM2

Sono implementati i seguenti parametri:

    - PR1

          Richiedi lo stato del tripode spinitalia, i possibili valori sono:

            OK PR1: 1, Spento
            OK PR1: 2, Emergenza
            OK PR1: 3, Attivo
            OK PR1: 4, Inizializzato
            OK PR1: 5, In ricerca del centro
            OK PR1: 6, Centrato
						OK PR1: 7, In analisi del file fornito
            OK PR1: 8, Simulazione
            OK PR1: 9, Fermo
            OK PR1: A, In centraggio
            OK PR1: B, Rilasciato
						OK PR1: C, Libero
            OK PR1: D, User not logged in

    - PR2

          Viene richiesta la posizione corrente della piattaforma.

            R:34.100 P:12.200 Y:330.200
            OK PR2

    - PR3 A[R|P|Y] L00.000 U00.000

          Imposta i limiti di uno dei tre giunti ( Roll, Pitch, Yaw ),
          tramite due valori, Lower ed Upper.

    - PR4 192.168.178.2 255.255.255.0 192.168.178.1

          Imposta l'Ip/Netmask/Getaway

    - PR5 M121 O60FB S005 T8u 0F

          Imposto a 0Fh il parametro con sub-index 5 dell'oggetto 60FBh
          con un 8bit unsigned ( <8/16/32><s/u> )

    - PR6 <user> <nuova_password>

          Imposta la password di accesso al sistema, che deve essere una
          stringa alfanumerica di 8-32 caratteri, scelti tra [0-9], [a-z],
          [A-Z], _ e -.

	      Il nome utente puo' essere 'alma3d_user'.

    - PR7

          Richiede l'MD5SUM dell'ultima simulazione convertita


6. Gestione degli errori asincroni
==================================

  Qualora si verificasse un errore durante il funzionamento del sistema, le
  seguenti affermazioni sono sempre vere:

    - Il sistema puo' interrompere il suo funzionamento e cambiare di stato
    - Lo stream sulla porta 10001 riporta lo stato 0
    - A qualsiasi comando inviato il sistema risponde con AERR, e poi
      con OK o ERR a seconda della gravita' dell'evento.

  Per conoscere lo stato del sistema e' possibile in ogni momento inviare il
  comando PR1.

6. Processi
===========

  - TesInterface: Permette l'accesso al sistema dall'esterno. Contiene il
    gestore della connessione ethernet, ed il parser del protocollo.
    Consente l'aggiornamento del sistema stesso.
  - CinematicaDiretta: Si occupa della conversione delle coordinate angolari
    dei giunti in coordinate angolari del tripode
  - CinematicaInversa: Si occupa della conversione delle coordinate angolari
    del tripode fornite in forma tabellare, in tanti file quanti i giunti in
    coordinate angolari dei giunti
  - GestoreMotori: Si occupa del dialogo con i motori, fornendogli
    costantemente coordinate da raggiungere nella loro tabella interna,
    avviando e arrestando la simulazione.


7. Funzionalita da implementare
===============================

  [Stati obbligatori]
  - Il sistema deve attendere una connessione in ingresso [CONNECTED]
  - Il sistema deve attendere un'autenticazione [AUTHENTICATED]
  - Reset del sistema e conteggio motori [RESET]
  - Il sistema esegue l'homing [HOMING]
  - Il sistema deve attendere una simulazione [SIMULATION_UPLOADED]
    - Errore in caso di MD5SUM del file errata
    - Errore nel caso di coordinata del singolo giunto errata
    - I file rimangono temporanei finche' non termina la procedura
    - La procedura termina se tutti i files sono presenti
  - Il sistema deve eseguire il self test senza arrivare al limite di
    movimentazione per evitare di sbattere ad ostacoli [SELFTEST]
  - Solo dopo posso avviare

  [Stati facoltativi]
  - Viene avviata una simulazione
    - Vengono restituite le coordinate attuali
      - Errore della conversione, non bloccante
    - La percentuale di completamento

  [Stati sempre attivi]
  - Intrusione nel perimetro
  - Problemi stato motori
  - Stato del tripode indipendente dalla simulazione
  - Problemi di comunicazione CAN/CANOPEN
  - Quanti motori sono attivi e' compito di TesIntf chiederlo e segnalere
    l'errore ( La configurazione del tripode risiede in TesIntf )
  - TesIntf deve eseguire lo zero
  - TesIntf deve eseguire una manovra dimostrativa
  - TesIntf deve spostare il tripode in posizione attacca antenna
  - TesIntf ha la posizione dall'homing configurata per giunti
  - USB-AUTOMOUNT deve eseguire l'upgrade del firmware e del kernel

8. Unittest
===========

  - Ricezione del file
    - Elaborazione con cinematica inversa fittizia
  - Autenticazione


A. Grandezze utilizzate
=======================

  [Pubbliche]
  <roll>:      -45.00 ... +45.00
  <pitch>:     -45.00 ... +45.00
  <yaw>:         0.00 ... 360.00
  <tempo>:          1 ... 256000
  <uint>:           0 ... 2^32 (unsigned int)
  <status>:         0 ... A

B. Stati del sistema
====================

Gli stati in cui puo' trovarsi il tripode sono i seguenti:

  - 0, Errore asincrono*
  - 1, Spento
  - 2, Emergenza
  - 3, Attivo
  - 4, Inizializzato
  - 5, In ricerca del centro
  - 6, Centrato
  - 7, In analisi del file fornito
  - 8, Simulazione
  - 9, Fermo
  - A, In centraggio
  - B, Rilasciato
  - C, Libero
  - D, Nessuna credenziale fornita

*) Per ragioni estranee al comando in esecuzione, si possono verificare errori che causano il blocco del
   sistema, come ad esempio un calo della tensione di alimentazione dei motori per l'eccessivo sforzo.
   Questa condizione e' indicata dallo stato 0. Per ottenere informazioni circa l'errore basta inviare un
   qualsiasi comando, e nella risposta verra' esplicitata la condizione di errore.

B. Riferimenti
==============

1. https://tools.ietf.org/html/rfc1321

2. http://www.md5summer.org/