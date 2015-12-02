=================================[ Manuale interno ]=================================

Rev.9 -- da confrontare con il manuale cliente! --
Data 1/09/2015


# Indice
========

  1. Descrizione generale
  2. Ricerca dell'indirizzo del tripode
  3. Invio di una simulazione
  4. Determinazione della posizione del tripode
  5. Operazioni con il tripode
  6. Inizializzazione del sistema Alma3d
  7. Gestione degli errori asincroni
  8. Processi
  9. Funzionalita da implementare
  10. Unittest

  A. Unita' di misura
  B. Stati del sistema
  C. Riferimenti


# 1. Descrizione generale
=========================

Il tripode Spinitalia Alma3D e' dotato di una connessione Ethernet 10/100
accessibile tramite il connettore RJ45 (CN09) del quadro di comando generale
(QCG).

Una volta connesso alla rete, il tripode si configura con un indirizzo IP 
statico pre-configurato. E' possibile modificare il suddetto indirizzo
tramite l'apposito comando.

All'avvio del sistema vengono eseguiti automaticamente due programmi: 
alma3d_canopenshell, che controlla i motori con comandi a basso livello, e
Alma3d, che rappresenta l'interfaccia tra il primo e l'esterno.

Il programma alma3d_canopenshell è scritto in c e si occupa di tradurre i
comandi passati al suo standard input nel linguaggio motori, nonchè 
inizializzare e gestire l'intero stack canopen. Ogni comunicazione da/verso
l'interfaccia Alma3d avviene tramite il suo standard input/output. Esiste un altro
canale di comunicazione per l'invio delle posizioni e dello stato dei motori
rappresentato da una pipe creata all'avvio del servizio. Questa esigenza nasce
dall'alta frequenza di aggiornamento delle suddette informazioni, che, altrimenti,
andrebbero a mascherare i comandi e le relative risposte, rendendo impossibile un
debug senza l'ausilio di un terzo programma per il parsing.

Nel proseguio del documento, i messaggi inviati dal programma canopenshell 
saranno indicati nel seguente modo:

    <<<< <messaggio da alma3d_canopenshell>

mentre quelli inviati al programma canopenshell saranno indicati nel seguente
modo:

    >>>> <messaggio per alma3d_canopenshell>

infine, essendo a senso unico, i messaggi provenienti dal programma 
alma3d_canopenshell saranno segnati semplicemente come segue:

    %%%% <informazioni dalla pipe >

Il programma Alma3d detiene il controllo del sistema ospitando tra i suoi
thread il software canopenshell. L'utente si interfaccia direttamente con
lui tramite una connessione tcp ed i messaggi scambiati vengono parzialmente
interpretati per poi essere passati al controllo motori. Alma3d implementa al
suo interno anche gli algoritmi per la conversione del file simulazione csv in
"file motori" e per la decodifica delle posizioni motori nella terna
roll/pitch/yaw (chiamati rispettivamente cinematica inversa e diretta). Un altro
compito demandato a questa unità è la gestione della barriera infrarossi.
Come alma3d_canopenshell, Alma3d utilizza un altro canale di comunicazione, in questo
caso un'altra porta tcp, per l'invio della posizione attuale del sistema nel formato
RPY.

Nel proseguio del documento, i messaggi inviati dal programma Alma3d al programma 
canopenshell saranno indicati nel seguente modo:

    >>>> <messaggio da Alma3d a alma3d_canopenshell>

quelli inviati dal programma Alma3d al client tcp:

    <tcp< <messaggio da Alma3d a client tcp>

quelli inviati al programma Alma3d dal client tcp:

    >tcp> <messaggio da client tcp a Alma3d>

infine, le informazioni inviate sul secondo canale di comunicazione:

    %tcp% <informazioni stato tripode>

# 2. Ricerca dell'indirizzo del tripode
========================================

Un metodo per trovare l'ip consiste nel richidere la risoluzione
inversa al server WINS del computer SPINITALIA_ALMA3D.


# 3. Invio di una simulazione
==============================

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

Per memorizzare un file della simulazione all'interno del sistema, basta 
accedere alla directory condivisa \\SPINITALIA-ALMA3D\simulazioni e 
salvarlo al suo interno.


# 4. Determinazione della posizione del tripode
================================================

## 4.1. Determinazione delle posizioni dal programma alma3d_canopenshell
========================================================================

Il programma alma3d_canopenshell apre una pipe all'avvio, che si trova nella
directory /tmp e ha nome fake_alma_3d_spinitalia_pos_stream_pipe se in
funzionamento virtuale oppure alma_3d_spinitalia_pos_stream_pipe se in
funzionamento reale.

Una volta aperta fornisce le seguenti informazioni secondo il seguente
formato:

  %%%% @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS6 T9 C0

Le informazioni fornite possiedono la seguente notazione:

  Sigla | Descrizione                        | Range valori
  ------|------------------------------------|------------------
  (@M)  | Indirizzo motore:                  | 119 ... 122
  (S)   | Step del motore:                   | -320000 ... 320000 (+-2^31)
  (AS)  | Alma status: stato del tripode     | (vedi appendice B)
  (T)   | Periodo di invio dei messaggi [ms] | 0.00 ... 999.99 (tipico 10.00)
  (C)   | Progresso analisi/simulazione [%]  | 0 ... 100

Esempio:

  %%%% @M119 S0 @M120 S100 @M121 S1234 @M122 S320000 AS6 T9.98 C0


I motori identificati come @M120...122 comandano i tre pistoni verticali, 
possiedono 8000 step in un giro, ed in ogni giro si elevano di 10mm. Lo 
zero corrisponde ad un altezza di 400mm più e l'escurione totale ad 800mm.
La distanza centro sfera centro cerniera dei pistoni e' di 1285mm.
Il motore identificato come @M119 comanda la rotazione del piatto, possiede
8000 step in un giro e la movimentazione passa attraverso un riduttore da
1:115. 

## 4.2. Determinazione delle posizioni dal programma Alma3d
========================================================================
Il sistema legge le informazioni sulla posizione fornite da alma3d_canopenshell
in step motore, le trasforma le altezze dei pistoni e poi in angoli R, P e Y.

Connettendosi alla porta 10001 del tripode si puo' ricevere la posizione
dello stesso, che viene trasmessa come un flusso continuo di coordinate in
questa forma:

  %tcp% R12.321;P-2.23;Y0;AS0;T10;C0
  %tcp% R12.321;P-2.23;Y0;AS0;T10;C0

Il tempo, come nel caso di alma3d_canopenshell, rappresenta i ms intercorsi tra 
un'informazione e l'altra. Gli angoli ed il tempo sono espressi secondo la 
seguente notazione:

  Sigla | Descrizione       | Range valori
  ------|-------------------|------------------
  (R)   | Roll [gradi]      | -45.00 ... +45.00
  (P)   | Pitch [gradi]     | -45.00 ... +45.00
  (Y)   | Yaw [gradi]       | 0.00 ... 360.00
  (AS)  | Stato del tripode | (vedi appendice B)
  (T)   | Time [ms]         | 0.00 ... 999.99
  (C)   | Progress[%]       | 0 ... 100

Il tempo si intende come quello impiegato a raggiungere la posizione
indicata, e viene espresso in ms.


#5. Operazioni con il tripode
=============================

Il controllo del Tripode Spinitalia Alma 3d avviene tramite procotollo TCP
sulla porta 10002.

Per le possibili interazioni tra i comandi e gli stati si rimanda alla
figura 1 (tripode.png).

Le seguenti affermazioni circa il protocollo sono sempre valide:

    - I comandi restituiscono se a buon fine:

        se alma3d_canopenshell:
        <<<< OK <cmd>

        se Alma3d:
        <tcp< OK <cmd>

    - I comandi restituiscono se in errore:

        se alma3d_canopenshell:
        <<<< CERR <cmd> <num>: <descr>

        se Alma3d:
        <tcp< CERR <cmd> <num>: <descr>

    - Esistono errori non causati dall'esecuzione di un comando. In
      tal caso puo' essere restituito un errore asincrono oltre alla
      risposta normale al comando indicata nei punti precedenti:

        se alma3d_canopenshell:
        <<<< AERR <num>: <descr>

        se Alma3d:
        <tcp< AERR <num>: <descr>

I comandi sono codificati in modo che siano raggruppati in famiglie funzionali:

    Comando | Descrizione
    --------|------------------------------------------------
    LGN     | Accesso al sistema (LoGiN)
    CT<x>   | Avvio della procedura x (Comando Tripode)
    EM<x>   | Avvio del comando di emergenza x (EMergenza)
    PR<x>   | Lettura o scrittura del parametro x (PaRametro)

##5.1 Differenze tra i comandi Alma3d e quelli alma3d_canopenshell
===================================================================
Anche se il formato tra i comandi Alma3d e alma3d_canopenshell è simile, le due 
implementazioni possono presentare parametri diversi. La spiegazione di tali 
differenze risiede nel fatto che il primo implementa delle procedure
specifiche per l'applicazione, mentre il secondo rimane ad un livello di astrazione
più alto.

Di seguito vengono elencate le corrispondenze tra i comandi Alma3d e alma3d_canopenshell,
rimandando più avanti una descrizione più dettagliata.

  Alma3d                  | alma3d_canopenshell
  ------------------------|---------------------
   LGN                    |  -
  ------------------------|-------------------------------
   CT0 [Waa]              | CT0 M4
                          | [PR5 M120 O60FB S008 T32s xx]
                          | [PR5 M121 O60FB S008 T32s xx]
                          | [PR5 M121 O60FB S008 T32s xx]
   CT1 Raa Pbb Ycc Vdd    | CT1 M120 Pxx VMyy AMzz
                          | CT1 M121 Pxx VMyy AMzz
                          | CT1 M122 Pxx VMyy AMzz S
   CT2 P1                 | CT2 P1
   CT2 P2                 | CT2 P1
   CT2 P3                 | CT2 P3
   CT2 P4                 | CT1 M119 P312000 VMyy AMzz
                          | CT1 M120 P312000 VMyy AMzz
                          | CT1 M121 P312000 VMyy AMzz
                          | CT1 M122 P312000 VMyy AMzz S
   CT3 <nome file>        | -
   CT4                    | PR5 M120 O2101 S03 T16u 2
                          | PR5 M121 O2101 S03 T16u 2
                          | PR5 M122 O2101 S03 T16u 2
                          | PR5 M120 O2101 S03 T16u 3
                          | PR5 M121 O2101 S03 T16u 3
                          | PR5 M122 O2101 S03 T16u 3
                          | CT4
   CT5                    | CT5
   CT6                    | CT1 M119 P312000 VMyy AMzz
                          | CT1 M120 P312000 VMyy AMzz
                          | CT1 M121 P312000 VMyy AMzz
                          | CT1 M122 P312000 VMyy AMzz S
                          | CT6
  ------------------------|---------------------------------
   EM1                    | EM1
   EM2                    | EM2
  ------------------------|---------------------------------
   PR1                    | -
   PR2                    | -
   PR3 A[R|P|Y] Lxx Uyy   | -
   PR4 xxx yyy            | -
   PR5 Mxx Oyy Szz T8u ww | PR5 Mxx Oyy Szz T8u ww
   PR6 xx yy              | -

##5.2 Descrizione comandi Alma3d
================================
Qui di seguito viene riportato l'elenco completo le procedure implementate:

    - LGN <user> <password>

        Accede al sistema tramite le credenziali fornite. Il nome utente
        e' fisso, 'alma_user', mentre la password di default e' 
        'spinitalia'.
        Per l'accesso come amministratore in caso di manutenzione, basta
        loggarsi come 'alma3d_admin' e password da decidere.

        In caso di successo viene inviata la stringa:

          <tcp< OK LGN

        In caso di errore:

          <tcp< CERR LGN 0: Wrong password

        Esempio:
          >tcp> LGN alma_user pippo
          <tcp< CERR LGN 0: Wrong password

          >tcp> LGN alma_user spinitalia
          <tcp< OK LGN

    - CT0 [Wxx]
        Avvia la procedura di inizializzazione dei 4 motori 
        inviando il comando CT0 M4 al programma alma3d_canopenshell.
        Se l'inizializzazione va a buon fine, allora viene restuito:

          <tcp< OK CT0

        altrimenti:

          <tcp< CERR CT0 0: Motori dichiarati non trovati

        Esempio:
          >tcp>CT0
          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< CERR CT0 0: Motori dichiarati non trovati
          <tcp< CERR CT0 0: Motori dichiarati non trovati

          >tcp>CT0
          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< @A121
          <<<< @A122
          <<<< OK CT0
          <tcp< OK CT0

        Il parametro opzionale W indica il peso caricato sul piatto del
        tripode. Nel caso fosse presente, il programma Alma3d si occupa
        di mandare dei messaggi aggiuntivi per impostare il PID dei 
        motori per avere migliori prestazioni dinamiche.

        Esempio:
          >tcp>CT0 W100
          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< @A121
          <<<< @A122
          <<<< OK CT0
          <tcp< OK CT0

          >>>> PR5 M120 O60FB S008 T32s C3500
          <<<< OK PR5
          >>>> PR5 M121 O60FB S008 T32s C3500
          <<<< OK PR5
          >>>> PR5 M122 O60FB S008 T32s C3500
          <<<< OK PR5

    - CT1 R<roll> P<pitch> Y<yaw> V<% vel max>
        Porta il tripode nel punto identificato dalla terna RPY.
        Alma3d converte i punti dalle RPY in step motore tramite l'algoritmo 
        di cinematica inversa ed invia tanti comandi CT1 Mxx Pyy VMzz AMww
        da passare a alma3d_canopenshell. La velocità massima è definita in
        un file di configurazione chiuso ed il termine <% vel max> rappresenta
        la percentuale di velocità massima da utilizzare. Alma3d si preoccupa 
        anche di controllare se la destinazione finale impostata rientra
        nell'area di lavoro del tripode.

        Se i parametri sono corretti e l'operazione va a buon fine, viene
        restituito:

          <tcp< OK CT1

        altrimenti:

          <tcp< CERR CT1 0: 

        Per esempio, per spostare il tripode nella posizione R20 P10 Y360 con una
        velocità pari al 30% di quella massima:

          >tcp> CT1 R20 P10 Y360 V30
          >>>> CT1 M119 P1231232 VM123 AM124
          <<<< OK CT1
          >>>> CT1 M120 P320000 VM123 AM124
          <<<< OK CT1
          >>>> CT1 M121 P34587 VM123 AM124
          <<<< OK CT1
          >>>> CT1 M122 P3156 VM123 AM124 S
          <<<< OK CT1
          <tcp< OK CT1

    - CT2 P1

          Copia la posizione di HOME predefinita in ogni file dei 4 motori ed avvia la 
          procedura di ricerca il fine corsa. Questo comando serve per impostare la posizione
          iniziale dei motori i quali non presentano un encoder assoluto integrato.Una volta 
          conclusa la procedura, il tripode si trova nella posizione di HOME.

          In caso di successo, viene restituito:

            <tcp< OK CT2 P1

          altrimenti:

            <tcp< CERR CT2 P1

          Esempio:
            >tcp> CT2 P1
            >>>> CT2 P1
            <<<< CT2 P1
            <tcp< CT2 P1

    - CT2 P2

          Sposta il sistema nella posizione di HOME.

    - CT2 P3

          Rilascia il controllo dei motori con l'effetto dell'abbassamento
          dei pistoni per effetto gravità. Rimane comunque attivo il 
          freno-motore così da rallentarne la caduta.

    - CT2 P4

          Porta il sistema al minimo di altezza controllando la discesa inviando
          dei comandi CT1 a tutti i motori con impostata l'altezza minima raggiungibile.

          In caso di successo, viene restituito:

            <tcp< OK CT2 P4
          
          altrimenti:
 
            <tcp< CERR CT2 P4

       
          Esempio:

            >tcp> CT2 P4
            >>>> CT1 M119 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M120 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M121 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M122 P312000 VM300000 AM100
            <<<< OK CT1
            <tcp< OK CT2 P4
          

    - CT3 <nome file>

          Avvia il controllo della simulazione <nome file> che deve essere presente nella
          nella cartella condivisa '\\TRIPODEALMA3D\' 

          Se il contenuto del file risulta regolare, il comando restituisce:

            <tcp< OK CT3

          Durante la conversione, il processo indica la percentuale di
          completamento nello stream della porta 10001.

          Esempio:
            >tcp> CT3 simulazione.csv
            %tcp% R0;P0;Y0;AS7;T10.0;C0
            %tcp% R0;P0;Y0;AS7;T10.0;C1
            %tcp% R0;P0;Y0;AS7;T10.0;C5
                          .
                          .
                          .
            %tcp% R0;P0;Y0;AS7;T10.0;C100
            <tcp< OK CT3

    - CT4

          Per prima cosa abilita i limiti di giunto per i pistoni per garantire la
          movimentazione completa, ma li lascia disabilitati nel motore di
          rotazione (yaw).

            >>>> PR5 M120 O2101 S03 T16u 2
            >>>> PR5 M120 O2101 S03 T16u 3

          Avvia la simulazione e, una volta terminata, il sistema restituisce:

            <tcp< OK CT4

          Invece, nel caso la simulazione sia interrotta da un evento asincrono
          o da un comando, viene restituito:

            <tcp< CERR CT4

          Durante la simulazone, il processo indica la percentuale di
          completamento nello stream della porta 10001.

          Esempio:
            >tcp> CT4
            >>>> PR5 M120 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M121 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M122 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M120 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> PR5 M121 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> PR5 M122 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> CT4
            %%%% @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C0
            %tcp% R0.000;P0.000;Y0.000;AS7;T10.0;C0
            %%%% @M119 S100 @M120 S0 @M121 S0 @M122 S0 AS7 T10.00 C1
            %tcp% R0.123;P0.000;Y0.000;AS7;T10.0;C1
            %%%% @M119 S200 @M120 S0 @M121 S0 @M122 S0 AS7 T9.96 C5
            %tcp% R0.500;P0.000;Y0.000;AS7;T10.0;C5
                          .
                          .
                          .
            %%%% @M119 S-320000 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C100
            %tcp% R22.500;P0.000;Y0.000;AS7;T10.0;C100
            <<<< OK CT4
            <tcp< OK CT4

    - CT5

          Arresta la simulazione interrompendola. Questo comando e'
          l'unico ad essere accettato durante una simulazione, e
          provoca le seguenti risposte:

            CERR CT4 0: Simulazione interrotta
            OK CT5

          Esempio:
            >tcp> CT4
            >>>> PR5 M120 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M121 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M122 O2101 S03 T16u 2
            <<<< OK PR5
            >>>> PR5 M120 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> PR5 M121 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> PR5 M122 O2101 S03 T16u 3
            <<<< OK PR5
            >>>> CT4
            %%%% @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C0
            %tcp% R0.000;P0.000;Y0.000;AS7;T10.0;C0
            %%%% @M119 S100 @M120 S0 @M121 S0 @M122 S0 AS7 T10.00 C1
            %tcp% R0.123;P0.000;Y0.000;AS7;T10.0;C1
            %%%% @M119 S200 @M120 S0 @M121 S0 @M122 S0 AS7 T9.96 C5
            %tcp% R0.500;P0.000;Y0.000;AS7;T10.0;C5
                          .
                          .
                          .
            >tcp> CT5
            >>>> CT5
            <<<< CERR CT4 0: Simulazione interrotta
            <tcp< CERR CT4 0: Simulazione interrotta
            <<<< OK CT5
            <tcp< OK CT5

    - CT6

          Spegne il sistema portando il piano in posizione di riposo
          orizzontale alla sua altezza minima. Al termine dell'operazione
          invia:

            <tcp< OK CT6

          Successivamente esegue l'arresto completo del dispositivo.

          Esempio:
    
            >tcp> CT6
            >>>> CT1 M119 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M120 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M121 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT1 M122 P312000 VM300000 AM100
            <<<< OK CT1
            >>>> CT6
            <<<< OK CT6
            <tcp< OK CT6

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


##5.3 Descrizione comandi alma3d_canopenshell
=============================================
    - CT0 M<num motori>
        Invia un segnale di reset a tutti i dispositivi canopen
        presenti sul bus che ne impone la dichiarazione. Ad ogni motore
        che si dichiara viene generata in output la seguente stringa:

            <<<< @A<indirizzo motore>
        

        Se dopo un certo periodo di tempo i motori che si sono dichiarati
        sono proprio <num motori>, allora alma3d_canopenshell restituisce:

          <<<< OK CT0

        altrimenti:

          <<<< CERR CT0 0: Motori dichiarati non trovati

        Esempio:
          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< CERR CT0 0: Motori dichiarati non trovati

          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< @A121
          <<<< @A122
          <<<< @A123
          <<<< CERR CT0 0: Motori dichiarati non trovati

          >>>> CT0 M4
          <<<< @A119
          <<<< @A120
          <<<< @A121
          <<<< @A122
          <<<< OK CT0

    - CT1 M<motore> P<step> VM<velocità> AM<accelerazione> [S]

          Porta il tripode nel punto identificato dalle quattro coordinate in step dei motori, 
          con una velocita' <velocità> in unita' motore con un'accellerazione <accelerazione> 
          in unita' motore. 

          Se il comando viene impartito senza il parametro opzionale [S], il motore interessato
          carica la posizione finale, ma non viene avviato. Nel momento in cui viene inviato il 
          comando con il parametro [S], tutti i motori precaricati si avviano. Questo è un modo
          per far partire i movimenti comandati in modo sincrono.
          
          Se i parametri sono corretti e l'operazione va a buon fine, viene
          restituito:

            <tcp< OK CT1

          altrimenti:

            <tcp< CERR CT1

          Esempio:
            >>>> CT1 M119 P1231232 VM123 AM124
            <<<< OK CT1
            >>>> CT1 M120 P320000 VM123 AM124
            <<<< OK CT1
            >>>> CT1 M121 P34587 VM123 AM124
            <<<< OK CT1
            >>>> CT1 M122 P3156 VM123 AM124 S
            <<<< OK CT1

          I parametri <velocità> ed <accelerazione> sono espressi in unità
          proprietarie del motore. Per convertire una velocità espressa in
          giri al secondo, oppure un'accelerazione espressa in giri al 
          secondo^2, utilizzare le seguenti formule:

          VT = Velocity * 65536      ( Giri al secondo   )
          AT = Acceleration * 8192   ( Giri al secondo^2 )

          Per l'attuatore rotativo, questi valori diventano:

          VT = Velocity * 65536 * 115 / 360     ( Gradi al secondo   )
          AT = Acceleration * 8192 * 115 / 360  ( Gradi al secondo^2 )

          Per l'attuatore lineare, questi valori diventano:

          VT = Velocity * 65536 * 10     ( mm al secondo   )
          AT = Acceleration * 8192 * 10  ( mm al secondo^2 )

    - CT2 P1

          Avvia la procedura di ricerca il fine corsa di tutti i motori e si
          sposta nella posizione configurata come HOME. La posizione di HOME
          e la velocità di spostamento per la ricerca vengono letti dal file 
          motore .mot, il quale deve contenere la stringa nel giusto formato
          (vedi "I file di simulazione")

          In caso di successo, viene restituito:

            <tcp< OK CT2 P1

          altrimenti, nel caso la stringa di homing non fosse conforme al formato
          atteso:

            <tcp< CERR CT2 P1

          Esempio:
            >tcp> CT2 P1
            >>>> CT2 P1
            <<<< CT2 P1
            <tcp< CT2 P1

    - CT2 P2
          Sposta il sistema nella posizione di HOME.

    - CT2 P3

          Rilascia il controllo dei motori con l'effetto dell'abbassamento
          dei pistoni per effetto gravità. Rimane comunque attivo il 
          freno-motore così da rallentarne la caduta.

    - CT4

          Avvia la simulazione prendendo le posizioni dai file motori .Una volta 
          terminata, il sistema restituisce:

            <<<< OK CT4

          Invece, nel caso la simulazione sia interrotta da un evento asincrono
          o da un comando, viene restituito:

            <<<< CERR CT4

          Durante la simulazone, la percentuale di completamento viene aggiornata 
          nello stream della pipe:

          Esempio:
            >>>> CT4
            %%%% @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C0
            %%%% @M119 S100 @M120 S0 @M121 S0 @M122 S0 AS7 T10.00 C1
            %%%% @M119 S200 @M120 S0 @M121 S0 @M122 S0 AS7 T9.96 C5
                          .
                          .
                          .
            %%%% @M119 S-320000 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C100
            <<<< OK CT4

    - CT5

          Arresta la simulazione interrompendola. Questo comando e'
          l'unico ad essere accettato durante una simulazione, e
          provoca le seguenti risposte:

            CERR CT4 0: Simulazione interrotta
            OK CT5

          Esempio:
            >>>> CT4
            %%%% @M119 S0 @M120 S0 @M121 S0 @M122 S0 AS7 T9.98 C0
            %%%% @M119 S100 @M120 S0 @M121 S0 @M122 S0 AS7 T10.00 C1
            %%%% @M119 S200 @M120 S0 @M121 S0 @M122 S0 AS7 T9.96 C5
                          .
                          .
                          .
            >>>> CT5
            <<<< CERR CT4 0: Simulazione interrotta
            <<<< OK CT5

    - CT6

          Rilascia tutte le risorse canopen e chiude il programma. Appena prima 
          della chiusura, viene inviato:

            <<<< OK CT6


          Esempio:
    
            >>>> CT6
            <<<< OK CT6


##5.4 I file di simulazione
======================================

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

#6. Inizializzazione del sistema Alma3d
=======================================
Una volta scoperto l'indirizzo IP, bisogna innanzitutto fornire le
credenziali di accesso al sistema, tramite il comando LGN. A seguito del
riconoscimento dell'utente è possibile interagire inviando gli altri
comandi.

7. Gestione degli errori asincroni
==================================

  Qualora si verificasse un errore durante il funzionamento del sistema, le
  seguenti affermazioni sono sempre vere:

    - Il sistema puo' interrompere il suo funzionamento e cambiare di stato
    - Lo stream sulla porta 10001 riporta lo stato 0
    - A qualsiasi comando inviato il sistema risponde con AERR, e poi
      con OK o ERR a seconda della gravita' dell'evento.

  Per conoscere lo stato del sistema e' possibile in ogni momento inviare il
  comando PR1.

8. Processi
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


9. Funzionalita da implementare
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

10. Unittest
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
