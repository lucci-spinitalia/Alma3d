=====================[ ALMA3D Spinitalia - Manuale del protocollo ]=====================

Rev.9a
Data 30/09/2015


Indice
======

  1. Descrizione generale
  2. Ricerca dell'indirizzo del tripode
  3. Invio di una simulazione
  4. Determinazione della posizione del tripode
  5. Operazioni con il tripode
  6. Gestione degli errori asincroni

  A. Unita' di misura
  B. Stati del sistema
  C. Riferimenti


1. Descrizione generale
=======================

Il tripode Spinitalia Alma3D e' dotato di una connessione Ethernet 10/100
accessibile tramite il connettore RJ45 (CN09) del quadro di comando generale (QCG).

Una volta connesso alla rete, viene assegnato all'interfaccia di rete un IP
fornito dal servizio DHCP presente, oppure con un IP statico se configurato.


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
  12,321;-2,23;0,001;200;commento opzionale
  12,321;-2,23;0,012;3210,3;

Non sono accettati celle vuote, ad esempio ";;30,0;;".

E' ignorata automaticamente la prima linea se contiene un'intestazione.

Gli angoli ed il tempo sono espressi secondo la seguente notazione:

  Roll:     -42.000 ... +42.000     gradi
  Pitch:    -45.000 ... +45.000     gradi
  Yaw:  -840000.000 ... +840000.000 gradi  (c.a */- 2300 giri)
  Time:           1 ... 256000  ms

Il tempo si intende come quello necessario a raggiungere la posizione
indicata, e viene espresso in ms, fino ad un massimo di 256000.

Una volta pronto il file bisogna calcolare l'hash MD5(rif. 1) dello stesso,
tramite ad esempio il programma md5summer (rif. 2). Il nome del file non
riveste particolare importanza, dal momento che il sistema distingue le
simulazioni dall'hash md5.

Per inviare un file della simulazione, basta accedere alla directory
condivisa \\SPINITALIA-ALMA3D\simulazioni e salvarlo al suo interno.


4. Determinazione della posizione del tripode
=============================================

Connettendosi alla porta 10001 del tripode si puo' ricevere la posizione
dello stesso, che viene trasmessa come un flusso continuo di coordinate in
questa forma:

  R12.321;P-2.23;Y0;AS0;T10;C0;avvio simulazione 33c995835f28604045b1256f645c9195
  R12.321;P-2.23;Y0;AS0;T10;C0

La simulazione viene identificata con l'hash md5. Gli angoli ed il tempo sono
espressi secondo la seguente notazione:

  (R)  Roll:        -42.00 ... +42.00 gradi
  (P)  Pitch:       -45.00 ... +45.00 degree
  (Y)  Yaw:    -840000.000 ... +840000.000 gradi
  (AS) Alma status: stato del tripode (vedi appendice B)
  (T)  Time:             10ms +/- 2ms
  (C)  Progress:         0 ... 100

Il tempo si intende come quello impiegato a raggiungere la posizione
indicata, e viene espresso in ms.

Il progresso si intende la percentuale di file analizzato a seguito di un
comando CT3 <MD5SUM>, oppure la percentuale di simulazione eseguita a seguito del
comando CT4 <MD5SUM>


5. Operazioni con il tripode
============================

Il controllo del Tripode Spinitalia Alma 3d avviene tramite procotollo TCP
sulla porta 10002.

Per le possibili interazioni tra i comandi e gli stati si rimanda alla
figura 1 (tripode.png).

Le seguenti affermazioni circa il protocollo sono sempre valide:

    - I comandi restituiscono se a buon fine:

        OK <cmd> <parametri opzionali>

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

          In caso di successo viene inviata la stringa:

						OK LGN

					In caso di errore:

            CERR LGN 0: Credenziali errate

    - CT0 [WXX]

          Avvia la procedura di inizializzazione del tripode, indicando
          opzionalmente il peso dell'antenna montata; Considerando
          montato un carico con una massa pari a 98Kg andra' inviata la
          stringa CT0 W98; Non volendo indicare il peso, verra' automaticamente
          impostato il peso predefinito di 50Kg, e puo' essere inviato
          semplicemente CT0.

          In caso di immissione di una massa diversa da quella reale, la
          piattaforma potrebbe non lavorare correttamente ed innescare
          errori asincroni.

          Normalmente il comando restituisce:

            OK CT0

          Se non vengono rilevati tutti i motori entro il periodo di
          ricerca, viene restituito l'errore:

            CERR CT0 0: Motori dichiarati non trovati

    - CT1 R32.100 P12.000 Y305 V10

          Muove nel punto desiderato Roll (32.1 gradi), Pitch (12 gradi),
          Yaw (305 gradi) con una velocità relativa del 10% (il campo V
          va da 0 a 100).

    - CT2 P1

          Avvia la procedura di ricerca dei fine corsa di tutti i motori e
          al termine, se correttamente trovati, si sposta nella posizione
          configurata come CENTRO.

    - CT2 P2

          Sposta il sistema nella posizione di home.

    - CT3 5757c1a61f2360039e0cb3c15a1cd69f

					Avvia il controllo della simulazione che deve essere presente
          nella cartella condivisa '\\SPINITALIA_ALMA3D\' con un HASH
          MD5SUM pari a 5757c1a61f2360039e0cb3c15a1cd69f.

					Se il contenuto del file risulta regolare, il comando restituisce:

            OK CT3

          Durante la conversione, il processo indica la percentuale di
          completamento nello stream della porta 10001.

		- CT4

          Avvia la simulazione precedentemente convertita.

					Quando e' terminata, il comando restituisce:

            OK CT4

    - CT5

           Arresta la simulazione interrompendola. Questo comando e'
           l'unico ad essere accettato durante una simulazione, e
           provoca le seguenti risposte:

             CERR CT4 0: Simulazione interrotta
             OK CT5

    - CT6

           Spegne il sistema portando il piano in posizione di riposo
           orizzontale alla sua altezza minima. Al termine dell'operazione
					 invia:

             OK CT6

					 Successivamente esegue l'arresto completo del dispositivo. Per
           accedere nuovamente al sistema e' necessario togliere e ripristinare
           l'alimentazione alla logica di 5V (Interruttore 5V.CPU sul QCG).

Sono implementate le seguenti procedure di emergenza:

    - EM1

           Rilascia tutti i motori. Normalmente restituisce:

             OK EM1

    - EM2

           Blocca tutti i motori ovunque essi siano. Normalmente restituisce:

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

          Viene richiesta la posizione corrente della piattaforma, normalmente
          il sistema risponde con:

            R34.100 P12.200 Y330
            OK PR2

          Se non e' stata ancora effettuata la ricerca del centro, restituisce:

            CERR PR2 0: Impossibile determinare la posizione

          Se la simulazione e' attiva, restituisce:

            CERR PR2 1: Comando non valido durante la simulazione, usare lo stream dati

    - PR3 A[R|P|Y] L00.000 U00.000

          Imposta i limiti di uno dei tre giunti ( Roll, Pitch, Yaw ), tramite due
          valori, Lower ed Upper.

          I limiti predefiniti sono i seguenti:

            Roll:       -42.00 ... +42.00 gradi
            Pitch:      -45.00 ... +45.00 gradi
            Yaw:   -840000.000 ... +840000.000 gradi  (c.a */- 2300 giri)

    - PR4 192.168.178.2 255.255.255.0 192.168.178.1

          Imposta l'Ip/Netmask/Getaway

	  - PR6 alma3d_user <nuova_password>

          Imposta la password di accesso al sistema, che deve essere una
          stringa alfanumerica di 8-32 caratteri, scelti tra [0-9], [a-z],
          [A-Z], _ e -.

          Normalmente viene restituito:

            OK PR6

    - PR7

          Richiede l'MD5SUM dell'ultima simulazione convertita. Se non e'
          stato eseguito il comando CT0 o CT2 P1 ed e' stata caricata una
          simulazione, il risultato e':

            OK PR7 9B99DBAD8F8F51913F6A82DD0A7B0C29

          Altrimenti, negli altri casi:

            CERR PR7 0: Nessuna simulazione caricata


6.. Gestione degli errori asincroni
==================================

  Qualora si verificasse un errore durante il funzionamento del sistema, le
seguenti affermazioni sono sempre vere:

  - Il sistema puo' interrompere il suo funzionamento e cambiare di stato
  - Lo stream sulla porta 10001 riporta lo stato 0
  - A qualsiasi comando inviato il sistema risponde con AERR, e poi con
    OK o ERR a seconda della gravita' dell'evento.

  Per conoscere lo stato del sistema e' possibile in ogni momento inviare il
comando PR1.


A. Grandezze utilizzate
=======================

  [Pubbliche]
  <roll>:       -42.00 ... +42.00
  <pitch>:      -45.00 ... +45.00
  <yaw>:   -840000.000 ... +840000.000 gradi  (c.a */- 2300 giri)
  <tempo>:           1 ... 256000
  <uint>:            0 ... 2^32 (unsigned int)


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

*) Per ragioni estranee al comando in esecuzione, si possono verificare
   errori che causano il blocco del sistema, come ad esempio un calo della
   tensione di alimentazione dei motori per l'eccessivo sforzo.
   Questa condizione e' indicata dallo stato 0. Per ottenere informazioni
   circa l'errore basta inviare un qualsiasi comando, e nella risposta
   verra' esplicitata la condizione di errore.


B. Riferimenti
==============

1. https://tools.ietf.org/html/rfc1321

2. http://www.md5summer.org/
