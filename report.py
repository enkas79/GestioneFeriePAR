"""
Modulo di generazione contenuti HTML (report PDF e guida utente).
Contiene solo funzioni pure di templating (nessuna dipendenza da Qt),
così da poter essere testate senza bisogno di un ambiente grafico.
"""

import html
from datetime import date
from typing import Dict, List, Tuple

import utils

# Colonne della tabella "Saldi" condivise fra la UI e il report PDF.
COLONNE_SALDI = (
    "Tipo", "Diritto annuo", "Residuo AP iniziale", "AP usato totale",
    "Maturato ad oggi", "Usato totale", "Residuo AP rimasto",
    "Disponibili oggi", "Presunto fine anno",
)


def riga_saldo_html(label: str, r: Dict[str, float]) -> str:
    """Costruisce la riga <tr> della tabella saldi per il report PDF (FERIE o PAR)."""
    return (
        f"<tr><td><b>{html.escape(label)}</b></td>"
        f"<td>{utils.format_ore_decimali(r.get('diritto', 0))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('res_ap_iniziale', r.get('res_ap', 0)))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('ap_scalato_totale', r.get('ap_scalato_anno_precedente', 0)))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('maturato', 0))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('goduto_tot', 0))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('res_ap_netto', 0))}</td>"
        f"<td class='s'>{utils.format_ore_decimali(r.get('saldo', 0))}</td>"
        f"<td>{utils.format_ore_decimali(r.get('presunto_fine_anno', 0))}</td></tr>"
    )


def riga_storico_html(data_display: str, tipo_display: str, ore_display: str, origine: str) -> str:
    """Costruisce la riga <tr> dello storico utilizzi per il report PDF."""
    return (
        "<tr>"
        f"<td>{html.escape(data_display)}</td>"
        f"<td>{html.escape(tipo_display)}</td>"
        f"<td>{html.escape(ore_display)}</td>"
        f"<td>{html.escape(origine)}</td>"
        "</tr>"
    )


def build_report_html(
    app_version: str,
    dipendente: str,
    matricola: str,
    data_assunzione_display: str,
    risultato_ferie: Dict[str, float],
    risultato_par: Dict[str, float],
    righe_storico: List[Tuple[str, str, str, str]],
) -> str:
    """Costruisce il documento HTML completo del report PDF (anagrafica, saldi, storico).

    `righe_storico` è una lista di tuple (data_display, tipo_display, ore_display, origine),
    già pronte per la visualizzazione (nessun escaping richiesto dal chiamante).
    """
    storico_rows = [riga_storico_html(*riga) for riga in righe_storico]
    if not storico_rows:
        storico_rows.append('<tr><td colspan="4">Nessuna assenza registrata.</td></tr>')
    storico_html = "\n".join(storico_rows)

    return f"""<html><head><style>
        body{{font-family:Arial,sans-serif;font-size:11pt;}}
        h1{{color:#0078d7;font-size:18pt;}}
        h3{{font-size:13pt;margin-top:15pt;margin-bottom:5pt;}}
        p{{font-size:11pt;margin-top:2pt;margin-bottom:2pt;}}
        table{{width:100%;border-collapse:collapse;margin-top:10pt;}}
        th,td{{border:1px solid #ccc;padding:6pt;text-align:center;font-size:10pt;}}
        th{{background-color:#f2f2f2;}}
        .s{{font-weight:bold;}}
        .small{{font-size:9pt;color:#555;}}
    </style></head><body>
        <h1>Report Ferie e PAR</h1>
        <p><b>Data Report:</b> {date.today().strftime("%d/%m/%Y")}</p><hr>
        <h3>Anagrafica</h3>
        <p><b>Dipendente:</b> {html.escape(dipendente)}</p>
        <p><b>Matricola:</b> {html.escape(matricola)}</p>
        <p><b>Data Assunzione:</b> {html.escape(data_assunzione_display)}</p>
        <br><h3>Dettaglio saldi</h3>
        <p><b>Nota:</b> valori espressi in ore decimali. 3,5 h = 3 ore e mezza.</p>
        <p><b>Programmazione:</b> le assenze personali future sono scalate prima dal Residuo AP;
           le date collettive restano scalate dai saldi dell'anno di competenza.</p>
        <table>
            <tr>{"".join(f"<th>{c}</th>" for c in COLONNE_SALDI)}</tr>
            {riga_saldo_html("FERIE", risultato_ferie)}
            {riga_saldo_html("PAR", risultato_par)}
        </table>

        <br><h3>Storico utilizzi completo</h3>
        <table>
            <tr><th>Data</th><th>Tipo</th><th>Ore</th><th>Origine</th></tr>
            {storico_html}
        </table>

        <br><p class="small">Generato da Gestione Ferie/PAR v{html.escape(app_version)}</p>
    </body></html>"""


def build_guida_html(app_version: str) -> str:
    """Costruisce la guida utente completa (mostrata nel dialogo "Aiuto > Guida Utente")."""
    v = html.escape(app_version)
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 11pt; line-height: 1.5; }}
            h1 {{ color: #0078d7; font-size: 16pt; }}
            h2 {{ color: #333; font-size: 13pt; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            h3 {{ color: #555; font-size: 12pt; }}
            .tip {{ background-color: #f0f8ff; padding: 8px; border-left: 3px solid #0078d7; margin: 10px 0; }}
            .warning {{ background-color: #fff8f0; padding: 8px; border-left: 3px solid #ff9900; margin: 10px 0; }}
            .version {{ font-style: italic; color: #666; text-align: right; }}
        </style>
    </head>
    <body>
        <h1>Gestione Ferie e PAR - Pro v{v}</h1>
        <p><b>Autore:</b> Enrico Martini</p>
        <p><b>Licenza:</b> MIT</p>
        <p class="version">Manuale aggiornato alla versione {v}</p>

        <hr>

        <h2>📌 Introduzione</h2>
        <p>
            <b>Gestione Ferie/PAR - Pro</b> è un'applicazione desktop professionale per la gestione,
            il calcolo e il monitoraggio dei saldi di <b>Ferie</b> e <b>PAR (Permessi Art. 2109)</b>.
            È stata sviluppata per semplificare la gestione delle assenze per i dipendenti,
            con particolare attenzione alle esigenze dei dipendenti Breton.
        </p>

        <h2>🚀 Funzionalità Principali</h2>

        <h3>1. Anagrafica Dipendente</h3>
        <p>
            Inserisci i dati personali del dipendente:
        </p>
        <ul>
            <li><b>Nominativo:</b> Nome e cognome del dipendente (obbligatorio).</li>
            <li><b>Matricola:</b> Codice identificativo aziendale.</li>
            <li><b>Data Assunzione:</b> Data di assunzione (utilizzata per calcolare l'anzianità).</li>
            <li><b>S. Patrono:</b> Spunta la casella per includere i +8h del Santo Patrono.</li>
        </ul>
        <div class="tip">
            <b>Suggerimento:</b> I dati vengono salvati automaticamente ogni volta che li modifichi.
        </div>

        <h3>2. Calendario Ferie Collettive</h3>
        <p>
            Gestisce l'estrazione intelligente dei giorni di chiusura collettiva (Cal) dalle email aziendali.
        </p>
        <ul>
            <li>Clicca sul pulsante <b>"Calendario Ferie"</b> per aprire la finestra di importazione.</li>
            <li>Incolla il testo della mail ufficiale aziendale che contiene le date di chiusura.</li>
            <li>Il programma <b>estrarra automaticamente</b> le date e le salverà.</li>
            <li>Le date del calendario vengono <b>scalate automaticamente</b> dai saldi come giornate
                intere da 8h.</li>
        </ul>
        <div class="tip">
            <b>Formati supportati:</b> Testo libero con date in formato "gg/mm/aaaa", "dal gg al gg mese aa",
            o elenchi di date. Il programma riconosce anche i tipi "FERIE" e "PAR".
        </div>

        <h3>3. Importazione Buste Paga (PDF Zucchetti)</h3>
        <p>
            Estrae automaticamente i Residui Anno Precedente (AP) e lo storico delle giornate
            direttamente dai cedolini in formato PDF Zucchetti.
        </p>
        <ul>
            <li>Clicca sul pulsante <b>"Carica Buste Paga"</b>.</li>
            <li>Seleziona uno o più file PDF (o TXT) contenenti le buste paga.</li>
            <li>Il programma estrae:
                <ul>
                    <li>Residuo AP Ferie e PAR.</li>
                    <li>Storico delle giornate godute nel mese (con data, tipo e ore).</li>
                </ul>
            </li>
            <li>Le assenze vengono aggiunte allo storico esistente (senza duplicati).</li>
        </ul>
        <div class="warning">
            <b>Attenzione:</b> Se la libreria <b>pypdf</b> non è installata, il pulsante sarà disabilitato.
            Installa con: <code>pip install pypdf</code>
        </div>

        <h3>4. Registrazione Manuale Assenze</h3>
        <p>
            Inserisci manualmente le assenze se non sono disponibili in formato digitale.
        </p>
        <ul>
            <li><b>Data:</b> Seleziona la data dell'assenza. Può essere anche futura: in quel caso viene
                indicata come <b>Programmata</b>.</li>
            <li><b>Periodo:</b> Spunta "Abilita Periodo" per inserire più giorni consecutivi.</li>
            <li><b>Tipo:</b> Seleziona <b>FERIE</b> o <b>PAR</b>.</li>
            <li><b>Ore:</b> Inserisci il numero di ore (massimo 8h/giorno).
                Se spunti "Giornata Intera", vengono inserite automaticamente 8h.</li>
            </li>
            <li>Clicca su <b>"Inserisci"</b> per aggiungere l'assenza.</li>
        </ul>
        <div class="tip">
            <b>Suggerimento:</b> Non puoi superare le 8 ore al giorno. Il programma avviserà in caso di errore.
        </div>

        <h3>5. Storico Utilizzi</h3>
        <p>
            Visualizza e gestisci lo storico delle assenze registrate.
        </p>
        <ul>
            <li>La tabella mostra <b>Data</b>, <b>Tipo</b> e <b>Ore</b> per ogni assenza.</li>
            <li>Le assenze personali future sono evidenziate con la scritta <b>(Programmata)</b>.</li>
            <li>Le assenze importate dal calendario sono evidenziate con lo sfondo giallo e la scritta
                <b>(Cal)</b>.</li>
            <li>Puoi <b>filtrare per anno</b> usando il menu a tendina in alto.</li>
            <li>Per <b>rimuovere</b> un'assenza, selezionala e premi <b>"Rimuovi Selezionati"</b> o il
                tasto <b>Canc</b>.</li>
            <li>Puoi <b>esportare lo storico in CSV</b> cliccando sul pulsante dedicato.</li>
        </ul>

        <h3>6. Saldi e Ore Disponibili</h3>
        <p>
            Visualizza i saldi aggiornati di Ferie e PAR in tempo reale.
        </p>
        <ul>
            <li><b>Diritto annuo:</b> Ore totali maturabili in un anno (160h + bonus anzianità).</li>
            <li><b>Residuo AP iniziale:</b> Residuo Anno Precedente inserito manualmente o importato da
                busta paga.</li>
            <li><b>AP usato totale:</b> Ore di Residuo AP già consumate, comprese le assenze personali
                future programmate che prenotano il Residuo AP prima del maturato corrente.</li>
            <li><b>Maturato ad oggi:</b> Ore maturate nell'anno corrente.</li>
            <li><b>Usato totale:</b> Ore totali utilizzate (normali + calendario).</li>
            <li><b>Residuo AP rimasto:</b> Residuo AP ancora disponibile.</li>
            <li><b>Disponibili oggi:</b> Ore totali disponibili (Residuo AP + Maturato).</li>
            <li><b>Presunto fine anno:</b> Stima delle ore disponibili a fine anno.</li>
        </ul>
        <div class="tip">
            <b>Metodo di calcolo:</b> Il programma usa un algoritmo <b>FIFO avanzato</b> che scala
            prima il Residuo AP e poi il Maturato corrente.
        </div>
        <div class="warning">
            <b>Attenzione:</b> Se il saldo diventa negativo, verrai avvisato con un messaggio in rosso.
        </div>

        <h3>7. Esportazione Report PDF</h3>
        <p>
            Genera un report completo in formato PDF con tutti i dati.
        </p>
        <ul>
            <li>Clicca sul pulsante <b>"Esporta in PDF"</b> o usa la scorciatoia <b>Ctrl+P</b>.</li>
            <li>Il report include:
                <ul>
                    <li>Dati anagrafici del dipendente.</li>
                    <li>Dettaglio dei saldi (Ferie e PAR).</li>
                    <li>Storico completo delle assenze.</li>
                </ul>
            </li>
            <li>Puoi salvare il file con il nome che preferisci.</li>
        </ul>

        <h3>8. Salvataggio e Backup</h3>
        <p>
            I dati vengono salvati automaticamente in un file locale.
        </p>
        <ul>
            <li><b>Formato:</b> JSON (o SQLite se configurato).</li>
            <li><b>Percorso:</b> <code>%APPDATA%\\\\FeParManager\\\\dati_ferie_par.json</code> (Windows)
                o <code>~/.local/share/FeParManager/dati_ferie_par.json</code> (Linux).</li>
            <li><b>Backup:</b> Vengono create automaticamente fino a 3 copie di backup rotanti
                (<code>.bak</code>, <code>.bak.1</code>, <code>.bak.2</code>) prima di ogni salvataggio.</li>
            <li><b>Crittografia:</b> Se impostata una password, i dati vengono cifrati con <b>AES-256</b>.</li>
        </ul>
        <div class="tip">
            <b>Suggerimento:</b> Puoi esportare il database completo dal menu
            <b>File &gt; Salva database come...</b>.
        </div>

        <h3>9. Aggiornamenti Automatici</h3>
        <p>
            Il programma verifica automaticamente la disponibilità di aggiornamenti.
        </p>
        <ul>
            <li><b>Controllo all'avvio:</b> Dopo 2 secondi dall'avvio, il programma verifica se c'è
                una nuova versione.</li>
            <li><b>Notifica:</b> Se è disponibile un aggiornamento, viene mostrata una finestra con:
                <ul>
                    <li>La versione disponibile.</li>
                    <li>La versione attuale.</li>
                    <li>Pulsante <b>"Scarica Ora"</b> per aprire la pagina di download.</li>
                    <li>Pulsante <b>"Più Tardi"</b> per chiudere la notifica.</li>
                </ul>
            </li>
            <li><b>Controllo manuale:</b> Puoi verificare gli aggiornamenti in qualsiasi momento
                dal menu <b>Aiuto &gt; Controlla Aggiornamenti</b>.</li>
        </ul>

        <h2>⌨️ Scorciatoie da Tastiera</h2>
        <table border="1" cellpadding="5" style="border-collapse: collapse; margin: 10px 0;">
            <tr>
                <th>Scorciatoia</th>
                <th>Azione</th>
            </tr>
            <tr>
                <td><b>Ctrl + S</b></td>
                <td>Salva i dati</td>
            </tr>
            <tr>
                <td><b>Ctrl + P</b></td>
                <td>Esporta report PDF</td>
            </tr>
            <tr>
                <td><b>Canc / Delete</b></td>
                <td>Rimuovi assenze selezionate</td>
            </tr>
        </table>

        <h2>🔧 Requisiti di Sistema</h2>
        <ul>
            <li><b>Python:</b> 3.8 o superiore.</li>
            <li><b>Librerie obbligatorie:</b>
                <ul>
                    <li><code>PyQt6</code> (interfaccia grafica).</li>
                    <li><code>pypdf</code> (importazione PDF, opzionale).</li>
                    <li><code>cryptography</code> (crittografia, opzionale).</li>
                </ul>
            </li>
            <li><b>Installazione:</b> <code>pip install -r requirements.txt</code></li>
        </ul>

        <h2>📄 Licenza</h2>
        <p>
            Questo software è distribuito sotto licenza <b>MIT</b>.
            Puoi liberamente usare, modificare e distribuire il programma,
            purché venga inclusa la licenza originale.
        </p>

        <hr>
        <p style="text-align: center; color: #666;">
            <b>Grazie per aver scelto Gestione Ferie/PAR - Pro!</b>
        </p>
    </body>
    </html>
    """
