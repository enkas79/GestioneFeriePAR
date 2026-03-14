# Gestione Ferie e PAR - Pro

Un'applicazione desktop professionale per la gestione, il calcolo e il monitoraggio dei saldi di Ferie e PAR, sviluppata in Python e PyQt6. 

## 🌟 Funzionalità Principali
* **Parsing Buste Paga:** Estrae in automatico i Residui Anni Precedenti e lo storico delle singole giornate direttamente dai cedolini in formato PDF (Zucchetti).
* **Calendario Intelligente:** Analizza il testo delle email aziendali per riconoscere e isolare i giorni di chiusura collettiva (Cal), scorporando i festivi e i weekend in automatico.
* **Calcolo Autonomo dei Saldi:** Applica logiche di scalamento (FIFO avanzato) scaricando i giorni prima dai Residui AP e poi dal Maturato corrente.
* **Esportazione:** Permette di salvare lo storico in formato CSV e generare un report formattato in PDF.
* **Aggiornamenti OTA:** Sistema integrato che avvisa l'utente se su GitHub è stata pubblicata una versione più recente del software.

## 🛠️ Tecnologie Utilizzate
* **Linguaggio:** Python 3.x
* **Interfaccia Grafica:** PyQt6
* **Lettura PDF:** pypdf
* **Architettura:** Object-Oriented Programming (OOP) con pattern Model-View (Separation of Concerns).

## 👨‍💻 Autore
**Enrico Martini**

## 📄 Licenza
Distribuito sotto licenza MIT. Vedi il file `LICENSE` per maggiori informazioni.
